import time
from django.core.management.base import BaseCommand
from log_query_site.models import PoliceLog
from log_query_site.geocoder import geocode_address


class Command(BaseCommand):
    help = "Geocode PoliceLog records that have no lat/lon yet"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Max records to process (0 = all)")
        parser.add_argument("--retry-failed", action="store_true", help="Re-geocode records marked as failed (lat=0, lon=0)")

    def handle(self, *args, **options):
        qs = PoliceLog.objects.filter(latitude__isnull=True, longitude__isnull=True)
        if options["limit"]:
            qs = qs[: options["limit"]]

        total = qs.count()
        self.stdout.write(f"Geocoding {total} records...")

        ok = 0
        fail = 0
        for i, record in enumerate(qs, 1):
            coords = geocode_address(record.address)
            if coords:
                record.latitude, record.longitude = coords
                record.save(update_fields=["latitude", "longitude"])
                ok += 1
            else:
                fail += 1

            if i % 50 == 0:
                self.stdout.write(f"  {i}/{total} processed ({ok} ok, {fail} failed)")

            # Nominatim rate limit: max 1 request/second
            time.sleep(1.1)

        self.stdout.write(self.style.SUCCESS(f"Done: {ok} geocoded, {fail} failed out of {total}"))
