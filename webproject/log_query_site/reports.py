from datetime import datetime, timedelta, date as date_type

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render

import redis as redis_client

from .models import PoliceLog, RecordType


def _parse_date(value):
    """Parse a YYYY-MM-DD string; return a date object or None."""
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def _find_gaps(queryset, start_date=None, end_date=None):
    """
    Find date ranges with no records within a PoliceLog queryset.

    Returns a tuple of (gaps, stats):
      gaps  — list of {'start', 'end', 'days'} dicts, newest-first
      stats — summary dict, or None when there is no data to analyse
    """
    qs = queryset.filter(datetime_start__isnull=False)
    if start_date:
        qs = qs.filter(datetime_start__date__gte=start_date)
    if end_date:
        qs = qs.filter(datetime_start__date__lte=end_date)

    dates_with_records = set(
        qs.values_list('datetime_start__date', flat=True).distinct()
    )

    if not dates_with_records:
        if start_date and end_date:
            total = (end_date - start_date).days + 1
            return (
                [{'start': start_date, 'end': end_date, 'days': total}],
                {
                    'analysis_start': start_date,
                    'analysis_end': end_date,
                    'total_days': total,
                    'days_with_records': 0,
                    'missing_days': total,
                    'gap_count': 1,
                    'longest_gap': total,
                    'coverage_pct': 0.0,
                },
            )
        return [], None

    analysis_start = start_date or min(dates_with_records)
    analysis_end = end_date or max(dates_with_records)
    total_days = (analysis_end - analysis_start).days + 1

    # Collect every missing date in the range
    missing = []
    current = analysis_start
    while current <= analysis_end:
        if current not in dates_with_records:
            missing.append(current)
        current += timedelta(days=1)

    # Collapse consecutive missing dates into gap ranges
    gaps = []
    if missing:
        gap_start = missing[0]
        gap_end = missing[0]
        for d in missing[1:]:
            if d == gap_end + timedelta(days=1):
                gap_end = d
            else:
                gaps.append({
                    'start': gap_start,
                    'end': gap_end,
                    'days': (gap_end - gap_start).days + 1,
                })
                gap_start = d
                gap_end = d
        gaps.append({
            'start': gap_start,
            'end': gap_end,
            'days': (gap_end - gap_start).days + 1,
        })

    days_with_records = total_days - len(missing)
    coverage_pct = round(days_with_records / total_days * 100, 1) if total_days else 0.0
    longest_gap = max((g['days'] for g in gaps), default=0)

    stats = {
        'analysis_start': analysis_start,
        'analysis_end': analysis_end,
        'total_days': total_days,
        'days_with_records': days_with_records,
        'missing_days': len(missing),
        'gap_count': len(gaps),
        'longest_gap': longest_gap,
        'coverage_pct': coverage_pct,
    }

    gaps.sort(key=lambda g: g['start'], reverse=True)
    return gaps, stats


@login_required
def reports_index(request):
    return render(request, 'log_query_site/reports/index.html')


@login_required
def report_geocode_queue(request):
    from log_site.celery import app as celery_app

    # ── Queue depth from Redis ────────────────────────────────────────────────
    pending = None
    redis_error = None
    try:
        r = redis_client.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        pending = r.llen('celery')
    except Exception as e:
        redis_error = str(e)

    # ── Live worker inspection (best-effort, 2 s timeout) ────────────────────
    active = reserved = scheduled = None
    workers_online = []
    inspect_error = None
    try:
        i = celery_app.control.inspect(timeout=2)
        active_map    = i.active()    or {}
        reserved_map  = i.reserved()  or {}
        scheduled_map = i.scheduled() or {}

        workers_online = sorted(set(active_map) | set(reserved_map) | set(scheduled_map))

        active = [
            {'worker': w, **t}
            for w, tasks in active_map.items()
            for t in tasks
        ]
        reserved = [
            {'worker': w, **t}
            for w, tasks in reserved_map.items()
            for t in tasks
        ]
        scheduled = [
            {'worker': w, **t}
            for w, tasks in scheduled_map.items()
            for t in tasks
        ]
    except Exception as e:
        inspect_error = str(e)

    # ── DB counts ─────────────────────────────────────────────────────────────
    ungeocoded_count = PoliceLog.objects.filter(latitude__isnull=True).count()
    geocoded_count   = PoliceLog.objects.filter(latitude__isnull=False).count()

    context = {
        'pending': pending,
        'redis_error': redis_error,
        'active': active or [],
        'reserved': reserved or [],
        'scheduled': scheduled or [],
        'workers_online': workers_online,
        'inspect_error': inspect_error,
        'ungeocoded_count': ungeocoded_count,
        'geocoded_count': geocoded_count,
    }
    return render(request, 'log_query_site/reports/geocode_queue.html', context)


@login_required
def report_ungeocoded(request):
    record_type_filter = request.GET.get('record_type', 'all')

    dispatch_type = RecordType.objects.filter(display_text='Dispatch').first()
    arrest_type = RecordType.objects.filter(display_text='Arrest').first()

    qs = PoliceLog.objects.filter(latitude__isnull=True).select_related(
        'record_type', 'officer', 'arrestee', 'dispatch_type', 'arrest_type'
    ).order_by('-datetime_start')

    if record_type_filter == 'dispatch' and dispatch_type:
        qs = qs.filter(record_type=dispatch_type)
    elif record_type_filter == 'arrest' and arrest_type:
        qs = qs.filter(record_type=arrest_type)

    total = qs.count()

    context = {
        'records': qs,
        'total': total,
        'record_type_filter': record_type_filter,
    }
    return render(request, 'log_query_site/reports/ungeocoded.html', context)


@login_required
def report_data_gaps(request):
    record_type_filter = request.GET.get('record_type', 'all')
    start_date = _parse_date(request.GET.get('start_date', ''))
    end_date = _parse_date(request.GET.get('end_date', ''))

    dispatch_type = RecordType.objects.filter(display_text='Dispatch').first()
    arrest_type = RecordType.objects.filter(display_text='Arrest').first()

    dispatch_result = arrest_result = None

    if record_type_filter in ('dispatch', 'all') and dispatch_type:
        qs = PoliceLog.objects.filter(record_type=dispatch_type)
        gaps, stats = _find_gaps(qs, start_date, end_date)
        dispatch_result = {'gaps': gaps, 'stats': stats}

    if record_type_filter in ('arrest', 'all') and arrest_type:
        qs = PoliceLog.objects.filter(record_type=arrest_type)
        gaps, stats = _find_gaps(qs, start_date, end_date)
        arrest_result = {'gaps': gaps, 'stats': stats}

    context = {
        'dispatch': dispatch_result,
        'arrest': arrest_result,
        'record_type_filter': record_type_filter,
        'start_date': start_date.isoformat() if start_date else '',
        'end_date': end_date.isoformat() if end_date else '',
    }
    return render(request, 'log_query_site/reports/data_gaps.html', context)
