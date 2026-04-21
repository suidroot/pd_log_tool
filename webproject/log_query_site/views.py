from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from datetime import datetime
import csv
import json

from django.conf import settings
from .auth import require_api_key
from .tasks import geocode_record
from .geocoder_control import is_paused, pause, resume

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

_ARREST_REQUIRED_FIELDS = ['arrestee', 'arrest_date', 'charge', 'arrest_type', 'officer']
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
    geocoded_count = PoliceLog.objects.filter(latitude__isnull=True).count()

    dispatch_type = RecordType.objects.filter(display_text='Dispatch').first()
    arrest_type = RecordType.objects.filter(display_text='Arrest').first()

    dispatches = PoliceLog.objects.filter(record_type=dispatch_type) if dispatch_type else PoliceLog.objects.none()
    arrests = PoliceLog.objects.filter(record_type=arrest_type) if arrest_type else PoliceLog.objects.none()

    counts = {
        "all_records": all_count,
        "geocoded_records": geocoded_count,
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

    arrest_str = ' '.join(data['arrest_date'].split())
    if not _parse_datetime(arrest_str, "%m/%d/%y %I:%M %p"):
        return JsonResponse({"error": "Invalid arrest_date format, expected MM/DD/YY HH:MM AM/PM"}, status=400)

    try:
        data["muni_short"] = 'PWM'
        data["record_type"] = 'arrest'
        record = PoliceLog.create_arrest(data)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": "Failed to create arrest record"}, status=500)

    try:
        geocode_record.delay(record.id)
    except Exception:
        pass  # broker unavailable — record saved, geocoding deferred to next geocode_records run
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
        date_str = ' '.join(data[date_field].split())
        if not _parse_datetime(date_str, fmt):
            return JsonResponse({"error": f"Invalid {date_field} format, expected MM/DD/YYYY HH:MM AM/PM"}, status=400)

    try:
        int(data['dispatch_number'])
    except (ValueError, TypeError):
        return JsonResponse({"error": "dispatch_number must be an integer"}, status=400)

    try:
        data["muni_short"] = 'PWM'
        data["record_type"] = 'dispatch'
        record = PoliceLog.create_dispatch(data)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": "Failed to create dispatch record"}, status=500)

    try:
        geocode_record.delay(record.id)
    except Exception:
        pass  # broker unavailable — record saved, geocoding deferred to next geocode_records run
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


def _filter_queryset(raw):
    """Apply search filters from a POST dict and return an ordered queryset."""
    fmt = "%Y-%m-%dT%H:%M"

    datetime_start_start = _parse_datetime(raw.get("datetime_start_start", ""), fmt)
    datetime_start_stop  = _parse_datetime(raw.get("datetime_start_stop",  ""), fmt)
    datetime_stop_start  = _parse_datetime(raw.get("datetime_stop_start",  ""), fmt)
    datetime_stop_stop   = _parse_datetime(raw.get("datetime_stop_stop",   ""), fmt)

    dispatch_type_id = raw.get("dispatch_type") or None
    officer_id       = raw.get("officer")        or None
    address          = raw.get("address")        or None
    charge           = raw.getlist("charge")     or None
    arrestee_id      = raw.get("arrestee")       or None
    arrestee_last    = raw.get("arrestee_last")  or None
    arrest_type_id   = raw.get("arrest_type")    or None
    record_type      = raw.get("record_type")    or None

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
    order_map = {
        "datetime_start": "-datetime_start",
        "datetime_stop":  "-datetime_stop",
        "arrestee":       "arrestee",
        "arrest_type":    "arrest_type",
        "officer":        "officer",
        "dispatch_type":  "dispatch_type",
    }
    results = results.order_by(order_map.get(sort, "-datetime_start"))
    return results


@login_required
def search_results(request):

    dispatch_number = request.POST.get("dispatch_number", None)

    if dispatch_number:
        results = get_object_or_404(PoliceLog, dispatch_number=dispatch_number)
        count = 1
        web_page = "log_query_site/single_dispatch_call_result.html"
        context = {"results": results, "count": count}
        return render(request, web_page, context)

    raw = request.POST
    try:
        page_size = int(raw.get("result_limit", MAX_RESULTS))
        if page_size < 1:
            page_size = MAX_RESULTS
    except (ValueError, TypeError):
        page_size = MAX_RESULTS

    try:
        page_number = int(raw.get("page", 1))
        if page_number < 1:
            page_number = 1
    except (ValueError, TypeError):
        page_number = 1

    qs = _filter_queryset(raw)
    total_count = qs.count()
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page_number)

    map_points = []
    for r in page_obj:
        if r.latitude and r.longitude:
            map_points.append({
                "lat": r.latitude,
                "lon": r.longitude,
                "label": str(r.record_type),
                "address": r.address,
                "date": str(r.datetime_start)[:10] if r.datetime_start else "",
            })

    provider_key = settings.MAP_TILE_PROVIDER
    tile_config = settings.MAP_TILE_PROVIDERS.get(provider_key, settings.MAP_TILE_PROVIDERS["carto-light"])

    # POST params for the replay form (export + pagination), strip stale page param
    post_params = [(k, v) for k, values in raw.lists() for v in values if k != "page"]

    context = {
        "results": page_obj,
        "count": total_count,
        "page_obj": page_obj,
        "paginator": paginator,
        "map_points_json": json.dumps(map_points),
        "map_tile": tile_config,
        "post_params": post_params,
    }
    return render(request, "log_query_site/search_results.html", context)


@login_required
def export_csv(request):
    results = _filter_queryset(request.POST)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="police_log_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "ID", "Type", "Dispatch #", "Date/Start", "Call Stop",
        "Arrestee", "Call Type", "Charges", "Arrest Type", "Officer", "Address",
    ])

    for r in results.select_related("record_type", "officer", "arrestee", "dispatch_type", "arrest_type").prefetch_related("charge"):
        writer.writerow([
            r.id,
            str(r.record_type),
            r.dispatch_number or "",
            r.datetime_start or "",
            r.datetime_stop or "",
            str(r.arrestee) if r.arrestee else "",
            str(r.dispatch_type) if r.dispatch_type else "",
            "; ".join(str(c) for c in r.charge.all()),
            str(r.arrest_type) if r.arrest_type else "",
            str(r.officer),
            r.address,
        ])

    return response


@login_required
@require_POST
def toggle_geocoder_pause(request):
    if is_paused():
        resume()
        action = 'resumed'
    else:
        pause()
        action = 'paused'
    return JsonResponse({'status': action})


@login_required
@require_POST
def queue_all_ungeocoded(request):
    ids = list(
        PoliceLog.objects.filter(latitude__isnull=True).values_list('id', flat=True)
    )
    queued = 0
    try:
        for pk in ids:
            geocode_record.delay(pk)
            queued += 1
    except Exception:
        return JsonResponse({"status": "error", "queued": queued, "message": "Queue unavailable"}, status=503)
    return JsonResponse({"status": "queued", "queued": queued})


@login_required
@require_POST
def trigger_geocode(request, record_id):
    record = get_object_or_404(PoliceLog, pk=record_id)

    if record.latitude is not None:
        return JsonResponse({"status": "already_geocoded"})

    try:
        geocode_record.delay(record.id)
    except Exception:
        return JsonResponse({"status": "error", "message": "Queue unavailable"}, status=503)

    return JsonResponse({"status": "queued"})
