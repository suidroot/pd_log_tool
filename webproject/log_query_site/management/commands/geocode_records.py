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
        reused = 0
        for i, record in enumerate(qs, 1):
            existing = (
                PoliceLog.objects
                .filter(address=record.address, latitude__isnull=False)
                .exclude(pk=record.pk)
                .values("latitude", "longitude")
                .first()
            )
            if existing:
                record.latitude = existing["latitude"]
                record.longitude = existing["longitude"]
                record.save(update_fields=["latitude", "longitude"])
                reused += 1
                ok += 1
                if i % 50 == 0:
                    self.stdout.write(f"  {i}/{total} processed ({ok} ok [{reused} reused], {fail} failed)")
                continue

            coords = geocode_address(record.address)
            if coords:
                record.latitude, record.longitude = coords
                record.save(update_fields=["latitude", "longitude"])
                ok += 1
            else:
                fail += 1

            if i % 50 == 0:
                self.stdout.write(f"  {i}/{total} processed ({ok} ok [{reused} reused], {fail} failed)")

            # Nominatim rate limit: max 1 request/second
            time.sleep(1.1)

        self.stdout.write(self.style.SUCCESS(f"Done: {ok} geocoded ({reused} reused from existing), {fail} failed out of {total}"))
