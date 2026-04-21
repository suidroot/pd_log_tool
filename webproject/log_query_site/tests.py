import hashlib
import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.http import QueryDict
from django.test import TestCase, Client
from django.utils import timezone

from .geocoder import _normalize_address, _expand_abbrevs, _is_intersection
from .models import (
    APIKey, Arrestee, ArrestType, Charge, DispatchType,
    GeocodeError, Municipality, Officer, PoliceLog, RecordType,
)
from .views import _filter_queryset


# ── Shared fixtures ───────────────────────────────────────────────────────────

def _make_municipality():
    muni, _ = Municipality.objects.get_or_create(
        short_name='PWM',
        defaults={'display_text': 'Portland', 'city': 'Portland', 'state': 'ME'},
    )
    return muni


def _make_record_types():
    dispatch, _ = RecordType.objects.get_or_create(display_text='Dispatch')
    arrest, _   = RecordType.objects.get_or_create(display_text='Arrest')
    return dispatch, arrest


def _make_api_key():
    raw = 'a' * 64
    prefix = raw[:8]
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    key = APIKey.objects.create(name='test', prefix=prefix, key_hash=key_hash)
    return key, raw


_DISPATCH_PAYLOAD = {
    'dispatch_number': '12345',
    'dispatch_start': '09/21/2023 02:15 AM',
    'dispatch_stop':  '09/21/2023 03:00 AM',
    'dispatch_type':  'Traffic Stop',
    'address':        '134 Congress St',
    'officer':        'Smith, John',
}

_ARREST_PAYLOAD = {
    'arrest_date':  '09/21/23 02:15 AM',
    'arrestee':     {'firstname': 'Jane', 'lastname': 'Doe', 'home_city': 'Portland', 'age': 30},
    'charge':       ['Assault'],
    'arrest_type':  'Warrant',
    'officer':      'Smith, John',
    'address':      '58 Boyd St',
}


# ── Geocoder helpers ──────────────────────────────────────────────────────────

class NormalizeAddressTests(TestCase):
    def test_plain_address_unchanged(self):
        self.assertEqual(_normalize_address("134 Congress St"), "134 Congress St")

    def test_strips_suite(self):
        self.assertEqual(_normalize_address("134 Congress St,Ste 1"), "134 Congress St")

    def test_strips_apartment(self):
        self.assertEqual(_normalize_address("58 Boyd St,Apt 208"), "58 Boyd St")

    def test_intersection_unchanged(self):
        self.assertEqual(_normalize_address("Riverside St/Forest Ave"), "Riverside St/Forest Ave")


class ExpandAbbrevsTests(TestCase):
    def test_expands_street(self):
        self.assertEqual(_expand_abbrevs("Riverside St"), "Riverside Street")

    def test_expands_avenue(self):
        self.assertEqual(_expand_abbrevs("Forest Ave"), "Forest Avenue")

    def test_multi_word(self):
        self.assertEqual(_expand_abbrevs("Brighton Ave"), "Brighton Avenue")

    def test_already_full(self):
        self.assertEqual(_expand_abbrevs("Congress Street"), "Congress Street")


class IsIntersectionTests(TestCase):
    def test_intersection_detected(self):
        self.assertTrue(_is_intersection("Riverside St/Forest Ave"))

    def test_plain_address_not_intersection(self):
        self.assertFalse(_is_intersection("134 Congress St"))


# ── Model: Officer ────────────────────────────────────────────────────────────

class OfficerModelTests(TestCase):
    def setUp(self):
        self.muni = _make_municipality()

    def test_creates_officer(self):
        officer = Officer.get_or_create(self.muni, 'John', 'Smith')
        self.assertIsNotNone(officer.pk)

    def test_deduplicates_officer(self):
        o1 = Officer.get_or_create(self.muni, 'John', 'Smith')
        o2 = Officer.get_or_create(self.muni, 'John', 'Smith')
        self.assertEqual(o1.pk, o2.pk)
        self.assertEqual(Officer.objects.filter(firstname='John', lastname='Smith').count(), 1)

    def test_different_names_are_separate(self):
        o1 = Officer.get_or_create(self.muni, 'John', 'Smith')
        o2 = Officer.get_or_create(self.muni, 'Jane', 'Doe')
        self.assertNotEqual(o1.pk, o2.pk)


# ── Model: Charge ─────────────────────────────────────────────────────────────

class ChargeModelTests(TestCase):
    def test_deduplicates_charge(self):
        c1 = Charge.get_or_create('assault')
        c2 = Charge.get_or_create('Assault')
        self.assertEqual(c1.pk, c2.pk)


# ── Model: PoliceLog dispatch ─────────────────────────────────────────────────

class PoliceLogDispatchTests(TestCase):
    def setUp(self):
        _make_municipality()
        _make_record_types()

    def _payload(self, **overrides):
        data = dict(_DISPATCH_PAYLOAD)
        data['muni_short'] = 'PWM'
        data.update(overrides)
        return data

    def test_creates_dispatch_record(self):
        record = PoliceLog.create_dispatch(self._payload())
        self.assertIsNotNone(record.pk)
        self.assertEqual(record.dispatch_number, 12345)

    def test_true_duplicate_returns_existing(self):
        r1 = PoliceLog.create_dispatch(self._payload())
        r2 = PoliceLog.create_dispatch(self._payload())
        self.assertEqual(r1.pk, r2.pk)

    def test_collision_offsets_dispatch_number(self):
        r1 = PoliceLog.create_dispatch(self._payload())
        # Same number, different address → not a true duplicate
        r2 = PoliceLog.create_dispatch(self._payload(address='99 Different St'))
        self.assertNotEqual(r1.pk, r2.pk)
        self.assertEqual(r2.dispatch_number, 12345 + 100000)

    def test_address_whitespace_normalised(self):
        record = PoliceLog.create_dispatch(self._payload(address='134  Congress   St'))
        self.assertEqual(record.address, '134 Congress St')

    def test_unknown_municipality_raises(self):
        with self.assertRaises(ValueError):
            PoliceLog.create_dispatch(self._payload(muni_short='ZZZ'))


# ── Model: PoliceLog arrest ───────────────────────────────────────────────────

class PoliceLogArrestTests(TestCase):
    def setUp(self):
        _make_municipality()
        _make_record_types()

    def _payload(self, **overrides):
        data = {
            'muni_short': 'PWM',
            'arrest_date': '09/21/23 02:15 AM',
            'arrestee': {'firstname': 'Jane', 'lastname': 'Doe', 'home_city': 'Portland', 'age': 30},
            'charge': ['Assault'],
            'arrest_type': 'Warrant',
            'officer': 'Smith, John',
            'address': '58 Boyd St',
        }
        data.update(overrides)
        return data

    def test_creates_arrest_record(self):
        record = PoliceLog.create_arrest(self._payload())
        self.assertIsNotNone(record.pk)
        self.assertEqual(record.charge.count(), 1)

    def test_multiple_charges_stored(self):
        record = PoliceLog.create_arrest(self._payload(charge=['Assault', 'Trespassing']))
        self.assertEqual(record.charge.count(), 2)

    def test_unknown_municipality_raises(self):
        with self.assertRaises(ValueError):
            PoliceLog.create_arrest(self._payload(muni_short='ZZZ'))


# ── Model: GeocodeError ───────────────────────────────────────────────────────

class GeocodeErrorModelTests(TestCase):
    def setUp(self):
        _make_municipality()
        _make_record_types()
        self.record = PoliceLog.create_dispatch({
            **_DISPATCH_PAYLOAD, 'muni_short': 'PWM',
        })

    def test_creates_not_found_error(self):
        err = GeocodeError.objects.create(
            record=self.record, address=self.record.address, error_type=GeocodeError.NOT_FOUND,
        )
        self.assertEqual(err.error_type, 'not_found')

    def test_survives_record_deletion(self):
        err = GeocodeError.objects.create(
            record=self.record, address=self.record.address, error_type=GeocodeError.NOT_FOUND,
        )
        self.record.delete()
        err.refresh_from_db()
        self.assertIsNone(err.record)
        self.assertEqual(err.address, '134 Congress St')


# ── Auth: require_api_key ─────────────────────────────────────────────────────

class APIKeyAuthTests(TestCase):
    def setUp(self):
        _make_municipality()
        _make_record_types()
        self.key, self.raw = _make_api_key()
        self.client = Client()

    def _post(self, raw_key=None, payload=None):
        headers = {}
        if raw_key is not None:
            headers['HTTP_AUTHORIZATION'] = f'Bearer {raw_key}'
        return self.client.post(
            '/add/dispatch/',
            data=json.dumps(payload or _DISPATCH_PAYLOAD),
            content_type='application/json',
            **headers,
        )

    def test_missing_auth_header_returns_401(self):
        resp = self._post(raw_key=None)
        self.assertEqual(resp.status_code, 401)

    def test_wrong_key_returns_401(self):
        resp = self._post(raw_key='wrong' * 13)
        self.assertEqual(resp.status_code, 401)

    def test_inactive_key_returns_401(self):
        self.key.is_active = False
        self.key.save()
        resp = self._post(raw_key=self.raw)
        self.assertEqual(resp.status_code, 401)

    @patch('log_query_site.views.geocode_record')
    def test_valid_key_is_accepted(self, mock_task):
        mock_task.delay.return_value = None
        resp = self._post(raw_key=self.raw)
        self.assertEqual(resp.status_code, 200)

    @patch('log_query_site.views.geocode_record')
    def test_valid_key_updates_last_used(self, mock_task):
        mock_task.delay.return_value = None
        self.assertIsNone(self.key.last_used)
        self._post(raw_key=self.raw)
        self.key.refresh_from_db()
        self.assertIsNotNone(self.key.last_used)


# ── View: add_dispatch ────────────────────────────────────────────────────────

class AddDispatchViewTests(TestCase):
    def setUp(self):
        _make_municipality()
        _make_record_types()
        _, self.raw_key = _make_api_key()
        self.client = Client()

    def _post(self, payload):
        return self.client.post(
            '/add/dispatch/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.raw_key}',
        )

    @patch('log_query_site.views.geocode_record')
    def test_valid_dispatch_returns_200(self, mock_task):
        mock_task.delay.return_value = None
        resp = self._post(_DISPATCH_PAYLOAD)
        self.assertEqual(resp.status_code, 200)

    @patch('log_query_site.views.geocode_record')
    def test_creates_record_in_db(self, mock_task):
        mock_task.delay.return_value = None
        self._post(_DISPATCH_PAYLOAD)
        self.assertTrue(PoliceLog.objects.filter(dispatch_number=12345).exists())

    def test_missing_required_field_returns_400(self):
        payload = dict(_DISPATCH_PAYLOAD)
        del payload['dispatch_number']
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('dispatch_number', resp.json()['error'])

    def test_invalid_date_format_returns_400(self):
        resp = self._post({**_DISPATCH_PAYLOAD, 'dispatch_start': '2023-09-21'})
        self.assertEqual(resp.status_code, 400)

    def test_non_integer_dispatch_number_returns_400(self):
        resp = self._post({**_DISPATCH_PAYLOAD, 'dispatch_number': 'abc'})
        self.assertEqual(resp.status_code, 400)

    def test_invalid_json_returns_400(self):
        resp = self.client.post(
            '/add/dispatch/', data='not json',
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.raw_key}',
        )
        self.assertEqual(resp.status_code, 400)

    @patch('log_query_site.views.geocode_record')
    def test_duplicate_dispatch_is_idempotent(self, mock_task):
        mock_task.delay.return_value = None
        self._post(_DISPATCH_PAYLOAD)
        resp = self._post(_DISPATCH_PAYLOAD)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PoliceLog.objects.filter(dispatch_number=12345).count(), 1)


# ── View: add_arrest ──────────────────────────────────────────────────────────

class AddArrestViewTests(TestCase):
    def setUp(self):
        _make_municipality()
        _make_record_types()
        _, self.raw_key = _make_api_key()
        self.client = Client()

    def _post(self, payload):
        return self.client.post(
            '/add/arrest/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.raw_key}',
        )

    @patch('log_query_site.views.geocode_record')
    def test_valid_arrest_returns_200(self, mock_task):
        mock_task.delay.return_value = None
        resp = self._post(_ARREST_PAYLOAD)
        self.assertEqual(resp.status_code, 200)

    @patch('log_query_site.views.geocode_record')
    def test_creates_record_in_db(self, mock_task):
        mock_task.delay.return_value = None
        self._post(_ARREST_PAYLOAD)
        self.assertEqual(PoliceLog.objects.count(), 1)

    def test_missing_required_field_returns_400(self):
        payload = dict(_ARREST_PAYLOAD)
        del payload['arrest_type']
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 400)

    def test_invalid_date_format_returns_400(self):
        resp = self._post({**_ARREST_PAYLOAD, 'arrest_date': '2023-09-21'})
        self.assertEqual(resp.status_code, 400)


# ── View: trigger_geocode ─────────────────────────────────────────────────────

class TriggerGeocodeViewTests(TestCase):
    def setUp(self):
        _make_municipality()
        _make_record_types()
        self.user = User.objects.create_user('tester', password='pass')
        self.client = Client()
        self.client.force_login(self.user)
        self.record = PoliceLog.create_dispatch({**_DISPATCH_PAYLOAD, 'muni_short': 'PWM'})

    def _post(self, record_id):
        return self.client.post(f'/records/{record_id}/geocode/')

    def test_unknown_record_returns_404(self):
        resp = self._post(99999)
        self.assertEqual(resp.status_code, 404)

    def test_already_geocoded_record(self):
        self.record.latitude = 43.66
        self.record.longitude = -70.25
        self.record.save()
        resp = self._post(self.record.pk)
        self.assertEqual(resp.json()['status'], 'already_geocoded')

    @patch('log_query_site.views.geocode_record')
    def test_ungeocoded_record_is_queued(self, mock_task):
        mock_task.delay.return_value = None
        resp = self._post(self.record.pk)
        self.assertEqual(resp.json()['status'], 'queued')
        mock_task.delay.assert_called_once_with(self.record.pk)


# ── View: search filter ───────────────────────────────────────────────────────

class SearchFilterTests(TestCase):
    def setUp(self):
        _make_municipality()
        _make_record_types()
        self.r1 = PoliceLog.create_dispatch({
            **_DISPATCH_PAYLOAD,
            'muni_short': 'PWM',
            'address': '134 Congress St',
        })
        self.r2 = PoliceLog.create_dispatch({
            **_DISPATCH_PAYLOAD,
            'dispatch_number': '99999',
            'muni_short': 'PWM',
            'address': '58 Boyd St',
        })

    def _qs(self, params):
        qd = QueryDict('', mutable=True)
        qd.update(params)
        return _filter_queryset(qd)

    def test_no_filters_returns_all(self):
        self.assertEqual(self._qs({}).count(), 2)

    def test_filter_by_address(self):
        qs = self._qs({'address': 'Congress'})
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.r1.pk)

    def test_filter_by_address_case_insensitive(self):
        qs = self._qs({'address': 'congress'})
        self.assertEqual(qs.count(), 1)

    def test_filter_by_record_type(self):
        dispatch_type = RecordType.objects.get(display_text='Dispatch')
        qs = self._qs({'record_type': str(dispatch_type.pk)})
        self.assertEqual(qs.count(), 2)

    def test_unknown_address_returns_empty(self):
        qs = self._qs({'address': 'Nowhere Lane'})
        self.assertEqual(qs.count(), 0)

    def _make_dated(self, number, date_str):
        return PoliceLog.create_dispatch({
            **_DISPATCH_PAYLOAD,
            'dispatch_number': number,
            'dispatch_start': date_str,
            'dispatch_stop':  date_str,
            'muni_short': 'PWM',
            'address': f'{number} Test St',
        })

    def test_sort_descending_by_default(self):
        self._make_dated('11001', '01/01/2022 08:00 AM')
        self._make_dated('11002', '06/15/2023 12:00 PM')
        qs = self._qs({'sort_radio': 'datetime_start'})
        dates = list(qs.values_list('datetime_start', flat=True))
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_sort_ascending(self):
        self._make_dated('11003', '01/01/2022 08:00 AM')
        self._make_dated('11004', '06/15/2023 12:00 PM')
        qs = self._qs({'sort_radio': 'datetime_start', 'sort_direction': 'asc'})
        dates = list(qs.values_list('datetime_start', flat=True))
        self.assertEqual(dates, sorted(dates))
