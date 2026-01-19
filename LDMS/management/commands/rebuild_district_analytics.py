import django
django.setup()

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils.timezone import now

from core.models import MasterDistrict
from LDMS.api.analytics_views import build_district_analytics

import logging
logger = logging.getLogger(__name__)

CACHE_TTL = 60 * 60 * 24  # 24 hours

class Command(BaseCommand):
    help = "Rebuild and cache district analytics for all districts"

    def handle(self, *args, **options):
        self.stdout.write("Starting district analytics rebuild...")

        for district_id in MasterDistrict.objects.values_list("district_id", flat=True):
            try:
                data = build_district_analytics(district_id)
                data["generated_at"] = now()

                cache_key = f"analytics:district:{district_id}"
                cache.set(cache_key, data, timeout=CACHE_TTL)

                self.stdout.write(f"✔ Cached district {district_id}")

            except Exception:
                logger.exception("Failed district %s", district_id)
                self.stderr.write(f"✖ Failed district {district_id}")

        self.stdout.write("District analytics rebuild completed.")
