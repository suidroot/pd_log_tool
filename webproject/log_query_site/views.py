from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from datetime import datetime
import json

from .auth import require_api_key

from .models import (
    PoliceLog,
    DispatchType,
    ArrestType,
    Charge,
    Officer,
    Arrestee,
    RecordType,
    Municipality
)

MAX_RESULTS = 100

_ARREST_REQUIRED_FIELDS = ['arrestee', 'arrest_date', 'charge', 'arrest_type', 'officer', 'address']
# officer is excluded: an empty string is valid and means "unknown officer"
_DISPATCH_REQUIRED_FIELDS = ['dispatch_number', 'dispatch_start', 'dispatch_stop', 'dispatch_type', 'address']


def _parse_datetime(value, fmt):
    """Return parsed datetime or None on failure."""
    try:
        return datetime.strptime(value, fmt)
    except (ValueError, AttributeError):
        return None


@login_required
def index(request):
    context = {}
    return render(request, "log_query_site/index.html", context)


@login_required
def about_page(request):

    municipalities = Municipality.objects.count()
    arrest_types = ArrestType.objects.count()
    officers = Officer.objects.count()
    arrestees = Arrestee.objects.count()
    charges = Charge.objects.count()
    dispatch_types = DispatchType.objects.count()

    all_count = PoliceLog.objects.count()

    dispatch_type = RecordType.objects.filter(display_text='Dispatch').first()
    arrest_type = RecordType.objects.filter(display_text='Arrest').first()

    dispatches = PoliceLog.objects.filter(record_type=dispatch_type) if dispatch_type else PoliceLog.objects.none()
    arrests = PoliceLog.objects.filter(record_type=arrest_type) if arrest_type else PoliceLog.objects.none()

    counts = {
        "all_records": all_count,
        'municipalities': municipalities,
        'arrest_types': arrest_types,
        'officers': officers,
        'arrestees': arrestees,
        'charges': charges,
        'dispatch_types': dispatch_types,
        'latest_dispatch_date': dispatches.order_by('-datetime_start').values_list('datetime_start', flat=True).first(),
        'first_dispatch_date': dispatches.order_by('datetime_start').values_list('datetime_start', flat=True).first(),
        'latest_arrest_date': arrests.order_by('-datetime_start').values_list('datetime_start', flat=True).first(),
        'first_arrest_date': arrests.order_by('datetime_start').values_list('datetime_start', flat=True).first(),
    }

    context = {"counts": counts}
    return render(request, "log_query_site/about.html", context)


@login_required
def logout_page(request):
    context = {}
    return render(request, "log_query_site/logout.html", context)


@csrf_exempt
@require_api_key
def add_arrest(request):

    if request.method != "POST":
        return HttpResponse("success", status=200)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    missing = [f for f in _ARREST_REQUIRED_FIELDS if not data.get(f)]
    if missing:
        return JsonResponse({"error": f"Missing required fields: {', '.join(missing)}"}, status=400)

    arrest_str = data['arrest_date'].replace('\n', ' ')
    if not _parse_datetime(arrest_str, "%m/%d/%y %I:%M %p"):
        return JsonResponse({"error": "Invalid arrest_date format, expected MM/DD/YY HH:MM AM/PM"}, status=400)

    try:
        data["muni_short"] = 'PWM'
        data["record_type"] = 'arrest'
        PoliceLog.create_arrest(data)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": "Failed to create arrest record"}, status=500)

    return HttpResponse("success", status=200)


@csrf_exempt
@require_api_key
def add_dispatch(request):

    if request.method != "POST":
        return HttpResponse("success", status=200)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    missing = [f for f in _DISPATCH_REQUIRED_FIELDS if not data.get(f)]
    if missing:
        return JsonResponse({"error": f"Missing required fields: {', '.join(missing)}"}, status=400)

    for date_field, fmt in [('dispatch_start', "%m/%d/%Y %I:%M %p"), ('dispatch_stop', "%m/%d/%Y %I:%M %p")]:
        date_str = data[date_field].replace('\n', ' ')
        if not _parse_datetime(date_str, fmt):
            return JsonResponse({"error": f"Invalid {date_field} format, expected MM/DD/YYYY HH:MM AM/PM"}, status=400)

    try:
        int(data['dispatch_number'])
    except (ValueError, TypeError):
        return JsonResponse({"error": "dispatch_number must be an integer"}, status=400)

    try:
        data["muni_short"] = 'PWM'
        data["record_type"] = 'dispatch'
        PoliceLog.create_dispatch(data)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": "Failed to create dispatch record"}, status=500)

    return HttpResponse("success", status=200)


@login_required
def show_dispatch_by_number(request, dispatch_number):

    results = get_object_or_404(PoliceLog, dispatch_number=dispatch_number)
    context = {"results": results}
    return render(request, "log_query_site/single_dispatch_result.html", context)


@login_required
def search_records(request):

    arrest_types = ArrestType.objects.all()
    officers = Officer.objects.all()
    arrestees = Arrestee.objects.all()
    charges = Charge.objects.all()
    record_types = RecordType.objects.all()
    dispatch_types = DispatchType.objects.all()

    context = {
        "municipalities": Municipality.objects.order_by("display_text"),
        "record_types": record_types.order_by("display_text"),
        "arrest_types": arrest_types.order_by("display_text"),
        "officers": officers.order_by("lastname"),
        "arrestees": arrestees.order_by("lastname"),
        "charges": charges.order_by("display_text"),
        "dispatch_types": dispatch_types.order_by("display_text"),
    }
    return render(request, "log_query_site/search_records.html", context)


@login_required
def search_results(request):

    dispatch_number = request.POST.get("dispatch_number", None)

    if dispatch_number:
        results = get_object_or_404(PoliceLog, dispatch_number=dispatch_number)
        count = 1
        web_page = "log_query_site/single_dispatch_call_result.html"

    else:
        raw = request.POST
        fmt = "%Y-%m-%dT%H:%M"

        datetime_start_start = _parse_datetime(raw.get("datetime_start_start", ""), fmt)
        datetime_start_stop = _parse_datetime(raw.get("datetime_start_stop", ""), fmt)
        datetime_stop_start = _parse_datetime(raw.get("datetime_stop_start", ""), fmt)
        datetime_stop_stop = _parse_datetime(raw.get("datetime_stop_stop", ""), fmt)

        dispatch_type_id = raw.get("dispatch_type") or None
        officer_id = raw.get("officer") or None
        address = raw.get("address") or None
        charge = raw.getlist("charge") or None
        arrestee_id = raw.get("arrestee") or None
        arrestee_last = raw.get("arrestee_last") or None
        arrest_type_id = raw.get("arrest_type") or None
        record_type = raw.get("record_type") or None

        try:
            limit = int(raw.get("result_limit", MAX_RESULTS))
            if limit < 1:
                limit = MAX_RESULTS
        except (ValueError, TypeError):
            limit = MAX_RESULTS

        results = PoliceLog.objects.all()

        if datetime_start_start and datetime_start_stop:
            results = results.filter(datetime_start__range=(datetime_start_start, datetime_start_stop))
        elif datetime_stop_start and datetime_stop_stop:
            results = results.filter(datetime_stop__range=(datetime_stop_start, datetime_stop_stop))

        if dispatch_type_id:
            results = results.filter(dispatch_type_id=dispatch_type_id)

        if officer_id:
            results = results.filter(officer=officer_id)

        if record_type and record_type != "all":
            results = results.filter(record_type=record_type)

        if arrestee_last:
            matched = Arrestee.objects.filter(lastname=arrestee_last.title())
            results = results.filter(arrestee__in=matched)
        elif arrestee_id:
            results = results.filter(arrestee=arrestee_id)

        if charge:
            results = results.filter(charge__in=charge)

        if arrest_type_id:
            results = results.filter(arrest_type=arrest_type_id)

        if address:
            results = results.filter(address__icontains=address)

        sort = raw.get("sort_radio", "datetime_start")
        if sort == "datetime_start":
            results = results.order_by("-datetime_start")
        elif sort == "datetime_stop":
            results = results.order_by("-datetime_stop")
        elif sort == "arrestee":
            results = results.order_by("arrestee")
        elif sort == "arrest_type":
            results = results.order_by("arrest_type")
        elif sort == "officer":
            results = results.order_by("officer")
        elif sort == "dispatch_type":
            results = results.order_by("dispatch_type")
        else:
            results = results.order_by("-datetime_start")

        count = results.count()
        results = results[:limit]
        web_page = "log_query_site/search_results.html"

    context = {"results": results, "count": count}
    return render(request, web_page, context)
