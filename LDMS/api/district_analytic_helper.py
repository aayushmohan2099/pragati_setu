import logging
from typing import Dict, Any, List

from django.conf import settings
from django.core.cache import cache

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import MasterBlock, MasterVillage
from core.api.upsrlm import (
    UpsrlmVoListView,
    UpsrlmClfListView,
)
from epSakhi.api.views import _call_apisetu_shg_list

logger = logging.getLogger(__name__)
DISTRICT_ANALYTICS_CACHE_KEY = "analytics:district:{district_id}"
DISTRICT_ANALYTICS_TTL = 60 * 60 * 24  # 24 hours

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _normalize_list(raw):
    """
    Normalize APISetu responses to list[dict]
    """
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("data") or raw.get("shg_list") or raw.get("shgList") or []
    return []

# District data helper
def build_district_analytics(district_id: int) -> dict:
    blocks = (
        MasterBlock.objects
        .filter(district_id=district_id)
        .values("block_id", "block_name_en")
    )

    result = {
        "district_id": district_id,
        "blocks": [],
    }

    for blk in blocks:
        block_id = blk["block_id"]

        try:
            vo_raw = UpsrlmVoListView().fetch_from_apisetu(
                f"analytics:vo:{block_id}",
                "vo/block",
                {"block_id": block_id},
            )
            clf_raw = UpsrlmClfListView().fetch_from_apisetu(
                f"analytics:clf:{block_id}",
                "clf/block",
                {"block_id": block_id},
            )
            shg_raw = _call_apisetu_shg_list(block_id)
        except Exception:
            logger.exception("Skipping block_id=%s due to API error", block_id)
            continue

        result["blocks"].append({
            "block_id": block_id,
            "block_name": blk["block_name_en"],
            "total_vos": len(_normalize_list(vo_raw)),
            "total_clfs": len(_normalize_list(clf_raw)),
            "total_shgs": len(_normalize_list(shg_raw)),
        })

    return result