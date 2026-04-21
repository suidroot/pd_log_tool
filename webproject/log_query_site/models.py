from datetime import datetime
from django.db import models, transaction, IntegrityError
from django.utils import timezone

def split_name(text_name):
    try:
        last, first = text_name.split(', ', 1)
    except ValueError:
        # Fallback for names not in "Last, First" format
        parts = text_name.split()
        if len(parts) >= 2:
            return {'firstname': parts[0], 'lastname': parts[1], 'middlename': ''}
        return {'firstname': text_name or 'unknown', 'lastname': 'unknown', 'middlename': ''}

    split_first = first.split()
    if len(split_first) > 1:
        name_dict = {
            'firstname': split_first[0],
            'lastname': last,
            'middlename': split_first[1],
        }
    else:
        name_dict = {
            'firstname': first,
            'lastname': last,
            'middlename': '',
        }

    return name_dict

class Municipality(models.Model):
    short_name = models.CharField(max_length=4, unique=True)
    display_text = models.TextField()
    city = models.TextField()
    state = models.TextField()

    def __str__(self):
        return f"{self.display_text}"

class RecordType(models.Model):
    display_text = models.TextField()

    def __str__(self):
        return f"{self.display_text}"

class Disposition(models.Model):
    display_text = models.TextField()

    def __str__(self):
        return f"{self.display_text}"

    @classmethod
    def search_by_name(cls, display_text):
        results = cls.objects.filter(display_text=display_text)
        count = results.count()
        if count == 0:
            return None
        if count > 1:
            raise Exception("Duplicate Disposition Detected")
        return results[0]

    @classmethod
    def get_or_create(cls, display_text):
        display_text = display_text.title()

        obj = cls.search_by_name(display_text)

        if not obj:
            obj = cls.create(display_text)
        
        return obj

    @classmethod
    def create(cls, display_text):
        display_text = display_text.title()
        obj = cls(display_text=display_text)
        obj.save()

        return obj

class DispatchType(models.Model):
    display_text = models.TextField()

    def __str__(self):
        return f"{self.display_text}"

    @classmethod
    def search_by_name(cls, display_text):
        results = cls.objects.filter(display_text=display_text)
        count = results.count()
        if count == 0:
            return None
        if count > 1:
            raise Exception("Duplicate Call Type Detected")
        return results[0]

    @classmethod
    def get_or_create(cls, display_text):
        display_text = display_text.title()

        obj = cls.search_by_name(display_text)

        if not obj:
            obj = cls.create(display_text)
        
        return obj

    @classmethod
    def create(cls, display_text):
        display_text = display_text.title()
        obj = cls(display_text=display_text)
        obj.save()

        return obj

class ArrestType(models.Model):
    display_text = models.TextField()

    def __str__(self):
        return f"{self.display_text}"

    @classmethod
    def search_by_name(cls, display_text):
        results = cls.objects.filter(display_text=display_text)
        count = results.count()
        if count == 0:
            return None
        if count > 1:
            return None
        return results[0]

    @classmethod
    def get_or_create(cls, display_text):
        display_text = display_text.title()

        obj = cls.search_by_name(display_text)

        if not obj:
            obj = cls.create(display_text)
        
        return obj

    @classmethod
    def create(cls, display_text):
        display_text = display_text.title()
        obj = cls(display_text=display_text)
        obj.save()
        return obj


class Charge(models.Model):
    display_text = models.TextField()

    def __str__(self):
        return f"{self.display_text}"
    
    @staticmethod
    def clean_name(text):

        text = text.replace("\n", "")
        text = text.strip()
        clean_text = text.title()

        return clean_text


    @classmethod
    def search_by_name(cls, display_text):

        if not cls.objects.filter(display_text=display_text).exists():
            results = None
        elif cls.objects.filter(display_text=display_text).count() > 1:
            results = None
        else:
            query_return = cls.objects.get(display_text=display_text)
            return query_return

        return results

    @classmethod
    def get_or_create(cls, display_text):
        display_text = cls.clean_name(display_text)

        obj = cls.search_by_name(display_text)

        if not obj:
            obj = cls.create(display_text)
        
        return obj

    @classmethod
    def create(cls, display_text):
        display_text = cls.clean_name(display_text)
        obj = cls(display_text=display_text)
        obj.save()
        return obj

class Officer(models.Model):
    municipality = models.ForeignKey(Municipality, on_delete=models.DO_NOTHING)
    firstname = models.TextField()
    lastname = models.TextField()
    middlename = models.TextField(default='')

    first_seen = models.DateTimeField(auto_now_add=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lastname}, {self.firstname}"

    @classmethod
    def search_by_name(cls, municipality, firstname, lastname, middlename=None):

        if not cls.objects.filter(municipality=municipality, firstname=firstname, \
                                  lastname=lastname).exists():
            results = None
        elif cls.objects.filter(municipality=municipality, firstname=firstname, \
                                  lastname=lastname).count() > 1:
            results = None
        else:
            query_return = cls.objects.filter(municipality=municipality, firstname=firstname, \
                                  lastname=lastname)
            return query_return[0]

        return results

    @classmethod
    def get_or_create(cls, municipality, firstname, lastname, middlename=None):

        firstname = firstname.capitalize()
        lastname = lastname.capitalize()

        obj = cls.search_by_name(municipality, firstname, lastname)

        if not obj:
            obj = cls.create(municipality, firstname, lastname)
        
        return obj

    @classmethod
    def create(cls, municipality, firstname, lastname, middlename=None):

        firstname = firstname.capitalize()
        lastname = lastname.capitalize()

        if middlename:
            middlename = middlename.capitalize()
            obj = cls(
                municipality=municipality,
                firstname=firstname,
                lastname=lastname,
                middlename=middlename,
            )
        else:
            obj = cls(
                municipality=municipality,
                firstname=firstname,
                lastname=lastname,
            )

        obj.save()
        return obj


class Arrestee(models.Model):
    firstname = models.TextField()
    lastname = models.TextField()
    middlename = models.TextField(default='')
    home_city = models.TextField()
    age = models.IntegerField()
    first_seen = models.DateTimeField(auto_now_add=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.firstname} {self.lastname} {self.middlename}"

    @classmethod
    def search_by_name(cls, firstname, lastname, middlename=None):
        results = cls.objects.filter(firstname=firstname, lastname=lastname)
        count = results.count()
        if count == 0:
            return None
        if count > 1:
            return None
        return results[0]

    @classmethod
    def get_or_create(cls, arrestee_dict):
        firstname = arrestee_dict['firstname'].capitalize()
        lastname = arrestee_dict['lastname'].capitalize()
        middlename = arrestee_dict.get('middlename', '').capitalize()

        obj = cls.search_by_name(firstname, lastname, middlename)

        if not obj:
            obj = cls.create(arrestee_dict)
        
        return obj

    @classmethod
    def create(cls, arrestee_dict):

        firstname = arrestee_dict['firstname'].capitalize()
        lastname = arrestee_dict['lastname'].capitalize()
        middlename = arrestee_dict.get('middlename', None)

        if middlename:
            middlename = middlename.capitalize()
            obj = cls(
                firstname=firstname,
                lastname=lastname,
                middlename=middlename,
                home_city=arrestee_dict['home_city'].title(),
                age=int(arrestee_dict['age']),
            )
        else:
            obj = cls(
                firstname=firstname,
                lastname=lastname,
                home_city=arrestee_dict['home_city'].title(),
                age=int(arrestee_dict['age']),
            )

        obj.save()

        return obj

class GeocodeError(models.Model):
    NOT_FOUND = 'not_found'
    RATE_LIMITED = 'rate_limited'
    NETWORK_ERROR = 'network_error'
    ERROR_TYPE_CHOICES = [
        (NOT_FOUND, 'Not Found'),
        (RATE_LIMITED, 'Rate Limited'),
        (NETWORK_ERROR, 'Network Error'),
    ]

    record = models.ForeignKey(
        'PoliceLog', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='geocode_errors',
    )
    address = models.TextField()
    error_type = models.CharField(max_length=20, choices=ERROR_TYPE_CHOICES)
    detail = models.TextField(blank=True, default='')
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-attempted_at']

    def __str__(self):
        return f"{self.get_error_type_display()} — {self.address} ({self.attempted_at:%Y-%m-%d %H:%M})"


class APIKey(models.Model):
    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=8, unique=True)
    key_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.prefix}...)"


class PoliceLog(models.Model):

    municipality = models.ForeignKey(Municipality, on_delete=models.DO_NOTHING)
    record_type = models.ForeignKey(RecordType, on_delete=models.DO_NOTHING)
    dispatch_number = models.IntegerField(unique=True, null=True)
    datetime_start = models.DateTimeField(null=True)
    datetime_stop = models.DateTimeField(null=True)
    dispatch_type = models.ForeignKey(DispatchType, on_delete=models.DO_NOTHING, null=True)
    disposition = models.ForeignKey(Disposition, on_delete=models.DO_NOTHING, null=True)
    officer = models.ForeignKey(Officer, on_delete=models.DO_NOTHING)
    arrestee = models.ForeignKey(Arrestee, on_delete=models.DO_NOTHING, null=True) # Table has name, home city and age
    charge = models.ManyToManyField(Charge) # can be multiple
    arrest_type = models.ForeignKey(ArrestType, on_delete=models.DO_NOTHING, null=True)
    address = models.TextField() # Violation Location
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):

        return f"{self.id} {self.datetime_start} {self.date_added}"

    @classmethod
    def create_dispatch(cls, media_log):
        try:
            municipality = Municipality.objects.get(short_name=media_log['muni_short'])
        except Municipality.DoesNotExist:
            raise ValueError(f"Unknown municipality: {media_log['muni_short']}")
        try:
            record_type = RecordType.objects.get(display_text='Dispatch')
        except RecordType.DoesNotExist:
            raise ValueError("RecordType 'Dispatch' not found — ensure initial data is loaded")
        dispatch_number = int(media_log['dispatch_number'])

        # 09/21/2023 
        # 02:15 AM
        dispatch_start = timezone.make_aware(datetime.strptime(' '.join(media_log['dispatch_start'].split()), "%m/%d/%Y %I:%M %p"))
        dispatch_stop  = timezone.make_aware(datetime.strptime(' '.join(media_log['dispatch_stop'].split()),  "%m/%d/%Y %I:%M %p"))
        
        dispatch_type = DispatchType.get_or_create(' '.join(media_log['dispatch_type'].split()))
        dispatch_address = ' '.join(media_log['address'].split()).title()

        officer_raw = ' '.join(media_log['officer'].split())
        if officer_raw == '':
            officer = Officer.get_or_create(municipality, 'unknown', 'unknown')
        else:
            officer_name = split_name(officer_raw)
            officer = Officer.get_or_create(municipality, officer_name['firstname'], officer_name['lastname'])

        obj = cls(
            municipality=municipality,
            record_type=record_type,
            dispatch_number=dispatch_number,
            datetime_start=dispatch_start,
            datetime_stop=dispatch_stop,
            dispatch_type=dispatch_type,
            address=dispatch_address,
            officer=officer
        )

        try:
            with transaction.atomic():
                obj.save()
        except IntegrityError:
            existing = cls.objects.filter(dispatch_number=dispatch_number).first()
            if existing and existing.datetime_start == dispatch_start and existing.address == dispatch_address:
                return existing  # true duplicate — skip
            # Different record sharing the same number — offset by 100000 until unique
            new_number = dispatch_number + 100000
            while cls.objects.filter(dispatch_number=new_number).exists():
                new_number += 100000
            obj.dispatch_number = new_number
            obj.save()

        return obj


    @classmethod
    def create_arrest(cls, arrest_log):
        try:
            municipality = Municipality.objects.get(short_name=arrest_log['muni_short'])
        except Municipality.DoesNotExist:
            raise ValueError(f"Unknown municipality: {arrest_log['muni_short']}")
        try:
            record_type = RecordType.objects.get(display_text='Arrest')
        except RecordType.DoesNotExist:
            raise ValueError("RecordType 'Arrest' not found — ensure initial data is loaded")
        # 09/21/2023 
        # 02:15 AM
        arrest_date = timezone.make_aware(datetime.strptime(' '.join(arrest_log['arrest_date'].split()), "%m/%d/%y %I:%M %p"))

        # Normalize whitespace on all incoming string fields
        arrestee_data = arrest_log['arrestee']
        arrestee_data['home_city'] = ' '.join(arrestee_data.get('home_city', '').split())
        arrestee = Arrestee.get_or_create(arrestee_data)

        arrest_type = ArrestType.get_or_create(' '.join(arrest_log['arrest_type'].split()))

        charges = []
        if isinstance(arrest_log['charge'], list):
            for charge_item in arrest_log['charge']:
                charges.append(Charge.get_or_create(' '.join(charge_item.split())))
        else:
            charges = [Charge.get_or_create(' '.join(arrest_log['charge'].split()))]

        officer_name = split_name(' '.join(arrest_log['officer'].split()))
        officer = Officer.get_or_create(municipality, officer_name['firstname'], officer_name['lastname'])

        arrest_address = ' '.join(arrest_log.get('address', '').split()).title()

        obj = cls(
            municipality=municipality,
            record_type=record_type,
            datetime_start=arrest_date,
            arrestee=arrestee,
            arrest_type=arrest_type,
            address=arrest_address,
            officer=officer,
        )

        with transaction.atomic():
            obj.save()
            obj.charge.set(charges)

        return obj