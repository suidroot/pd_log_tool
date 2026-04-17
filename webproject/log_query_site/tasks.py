from celery import shared_task
from .geocoder import geocode_address


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def geocode_record(self, record_id):
    from .models import PoliceLog
    try:
        record = PoliceLog.objects.get(pk=record_id)
    except PoliceLog.DoesNotExist:
        return

    if record.latitude is not None:
        return

    coords = geocode_address(record.address)
    if coords:
        record.latitude, record.longitude = coords
        record.save(update_fields=['latitude', 'longitude'])
    else:
        # Retry on failure; gives up after max_retries
        raise self.retry()
