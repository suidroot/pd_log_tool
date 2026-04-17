import logging
import time
from celery import shared_task
from .geocoder import geocode_address, GeocoderUnavailable, GeocoderRateLimited
from .geocoder_control import is_paused

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5, default_retry_delay=120, rate_limit='1/s')
def geocode_record(self, record_id):
    if is_paused():
        # Re-queue after 60 s so the task isn't lost while paused
        raise self.retry(countdown=60, max_retries=None)

    from .models import PoliceLog
    try:
        record = PoliceLog.objects.get(pk=record_id)
    except PoliceLog.DoesNotExist:
        return

    if record.latitude is not None:
        return

    # Reuse coordinates from another record with the same address
    existing = (
        PoliceLog.objects
        .filter(address=record.address, latitude__isnull=False)
        .exclude(pk=record.pk)
        .values('latitude', 'longitude')
        .first()
    )
    if existing:
        record.latitude = existing['latitude']
        record.longitude = existing['longitude']
        record.save(update_fields=['latitude', 'longitude'])
        return

    time.sleep(1.1)  # respect Nominatim 1 req/s policy

    try:
        coords = geocode_address(record.address)
    except GeocoderRateLimited as e:
        if self.request.retries >= 1:
            logger.error(
                "geocode_record: dropping record %s (%s) after rate-limit retry — %s",
                record_id, record.address, e,
            )
            return
        raise self.retry(exc=e, countdown=600, max_retries=1)
    except GeocoderUnavailable as e:
        raise self.retry(exc=e)

    if coords:
        record.latitude, record.longitude = coords
        record.save(update_fields=['latitude', 'longitude'])
    # None means address not found — leave ungeocoded, do not retry
