from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json

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

def index(request):
    context = {}
    return render(request, "log_query_site/index.html", context)

def about_page(request):

    municipalities =  Municipality.objects.count()
    arrest_types = ArrestType.objects.count()
    officers = Officer.objects.count()
    arrestees = Arrestee.objects.count()
    charges = Charge.objects.count()
    record_types = RecordType.objects.count()
    dispatch_types = DispatchType.objects.count()
    officers = Officer.objects.count()

    all_count = PoliceLog.objects.count()

    dispatch_type = RecordType.objects.get(display_text='Dispatch')
    arrest_type = RecordType.objects.get(display_text='Arrest')
    most_recent_dispatch = PoliceLog.objects.filter(record_type=dispatch_type).order_by('-datetime_start')[0]
    most_recent_arrest = PoliceLog.objects.filter(record_type=arrest_type).order_by('-datetime_start')[0]

    
    counts = {
        "all_records" : all_count,
        'municipalities' : municipalities,
        'arrest_types' : arrest_types,
        'officers' : officers,
        'arrestees' : arrestees,
        'charges' : charges,
        'dispatch_types' : dispatch_types,
        'latest_dispatch_date' : most_recent_dispatch.datetime_start,
        'latest_arrest_date' : most_recent_arrest.datetime_start,
    }

    context = {"counts" : counts}
    return render(request, "log_query_site/about.html", context)

def logout_page(request):
    context = {}
    return render(request, "log_query_site/logout.html", context)

@csrf_exempt 
def add_arrest(request):

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # TODO: Add field validation
            data["muni_short"] = 'PWM'
            data["record_type"] = 'arrest'
            entry = PoliceLog.create_arrest(data)
            entry.save()
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        
    return HttpResponse("success", status=200)

@csrf_exempt 
def add_dispatch(request):

    if request.method == "POST":
        
        try:
            data = json.loads(request.body)
            # TODO: Add field validation
            data["muni_short"] = 'PWM'
            data["record_type"] = 'dispatch'
            entry = PoliceLog.create_dispatch(data)
            entry.save()
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        
    return HttpResponse("success", status=200)

def show_dispatch_by_number(request, dispatch_number):

    results = PoliceLog.objects.filter(dispatch_number=dispatch_number)[0]
    context = {"results" : results}
    return render(request, "log_query_site/single_dispatch_result.html", context)

def search_records(request):

    municipalities =  Municipality.objects.all()
    arrest_types = ArrestType.objects.all()
    officers = Officer.objects.all()
    arrestees = Arrestee.objects.all()
    charges = Charge.objects.all()
    record_types = RecordType.objects.all()
    dispatch_types = DispatchType.objects.all()
    officers = Officer.objects.all()

    context = { 
        "municipalities" : municipalities.order_by("display_text"),
        "record_types" : record_types.order_by("display_text"),
        "arrest_types" : arrest_types.order_by("display_text"), 
        "officers" : officers.order_by("lastname"),
        "arrestees" : arrestees.order_by("lastname"),
        "charges" : charges.order_by("display_text"),
        "dispatch_types" : dispatch_types.order_by("display_text"),
    }
    return render(request, "log_query_site/search_records.html", context)

def search_results(request):

    dispatch_number = request.POST.get("dispatch_number", None)

    if dispatch_number:
        results = PoliceLog.objects.get(dispatch_number=dispatch_number)
        count = 1
        web_page = "log_query_site/single_dispatch_call_result.html"

    else:
        if "datetime_start_start" in request.POST and request.POST["datetime_start_start"]:
            datetime_start_start = datetime.strptime(request.POST["datetime_start_start"],"%Y-%m-%dT%H:%M")
        else:
            datetime_start_start = None
        
        if "datetime_start_stop" in request.POST and request.POST["datetime_start_stop"]:
            datetime_start_stop = datetime.strptime(request.POST["datetime_start_stop"],"%Y-%m-%dT%H:%M")
        else:
            datetime_start_stop = None

        if "datetime_stop_start" in request.POST and request.POST["datetime_stop_start"]:
            datetime_stop_start = datetime.strptime(request.POST["datetime_stop_start"],"%Y-%m-%dT%H:%M")
        else:
            datetime_stop_start = None

        if "datetime_stop_stop" in request.POST and request.POST["datetime_stop_stop"]:
            datetime_stop_stop = datetime.strptime(request.POST["datetime_stop_stop"],"%Y-%m-%dT%H:%M")
        else:
            datetime_stop_stop = None

        dispatch_type_id = request.POST.get("dispatch_type", None)
        officer_id = request.POST.get("officer", None)
        address = request.POST.get("address", None)

        if "charge" in request.POST and request.POST["charge"]:
            charge = request.POST.getlist("charge")
        else:
            charge = None

        arrestee_id = request.POST.get("arrestee", None)
        arrestee_last = request.POST.get("arrestee_last", None)
        officer_id = request.POST.get("officer", None)
        arrest_type_id = request.POST.get("arrest_type", None)
        record_type = request.POST.get("record_type", None)

        results = PoliceLog.objects.all()

        # Filters

        if datetime_start_start and datetime_start_stop:
            results = results.filter(datetime_start__range=(datetime_start_start, datetime_start_stop))
        elif datetime_stop_start and datetime_stop_stop:
            results = results.filter(datetime_stop__range=(datetime_stop_start, datetime_stop_stop))

        if dispatch_type_id:
            results = results.filter(dispatch_type_id=dispatch_type_id)

        if officer_id:
            results = results.filter(officer=officer_id)

        if record_type != "all":
            results = results.filter(record_type=record_type)

        if arrestee_last:
            arrestee_id = Arrestee.objects.filter(lastname=arrestee_last.title())
            results = results.filter(arrestee__in=arrestee_id)
        elif arrestee_id:
            results = results.filter(arrestee=arrestee_id)

        if charge:
            results = results.filter(charge__in=charge)

        if arrest_type_id:
            results = results.filter(arrest_type=arrest_type_id)

        if officer_id:
            results = results.filter(officer=officer_id)

        if address:
            results = results.filter(address__icontains=address)

        # Sort Data
        if request.POST["sort_radio"] == "datetime_start":
            results = results.order_by("datetime_start").reverse()
        elif request.POST["sort_radio"] == "datetime_stop":
            results = results.order_by("datetime_stop").reverse()
        elif request.POST["sort_radio"] == "arrestee":
            results = results.order_by("arrestee")
        elif request.POST["sort_radio"] == "arrest_type":
            results = results.order_by("arrest_type")
        elif request.POST["sort_radio"] == "officer":
            results = results.order_by("officer")
        elif request.POST["sort_radio"] == "dispatch_type":
            results = results.order_by("dispatch_type")
        else:
            results = results.order_by("datetime_start").reverse()

        # Limit results
        if "result_limit" in request.POST and request.POST["result_limit"]:
            limit = int(request.POST["result_limit"])
        else:
            limit = MAX_RESULTS

        if limit:
            results = results[:limit]

        count = results.count()

        web_page = "log_query_site/search_results.html"

    context = {"results" : results, "count" : count}

    return_render = render(request, web_page, context)


    return return_render

