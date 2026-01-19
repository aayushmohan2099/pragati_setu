# LDMS/api/analytics_views.py

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
from .district_analytic_helper import build_district_analytics

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


# ==================================================================
# Analytics API
# ==================================================================

class UpsrlmAnalyticsView(APIView):
    """
    GET /api/v1/analytics/upsrlm/

    Query Params:
      - block_id=<int>
      - district_id=<int>
      - detail=true|false

    Rules:
      - Either block_id OR district_id is required
      - detail=true works only with block_id
    """

    permission_classes = []  # internal / dashboard use

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def get(self, request):
        district_id = request.GET.get("district_id")
        block_id = request.GET.get("block_id")
        detail = str(request.GET.get("detail", "")).lower() in {"1", "true", "yes"}

        if not block_id and not district_id:
            return Response(
                {"detail": "block_id or district_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if block_id:
            return self._block_analytics(int(block_id), detail)

        return self._district_analytics(int(district_id))

    # ------------------------------------------------------------------
    # DISTRICT LEVEL ANALYTICS
    # ------------------------------------------------------------------

    def _district_analytics(self, district_id: int):
        cache_key = f"analytics:district:{district_id}"

        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        data = build_district_analytics(district_id)

        cache.set(cache_key, data, timeout=60 * 60 * 24)

        return Response(data)
    

    # ------------------------------------------------------------------
    # BLOCK LEVEL ANALYTICS
    # ------------------------------------------------------------------

    def _block_analytics(self, block_id: int, detail: bool):
        try:
            block = MasterBlock.objects.get(block_id=block_id)
        except MasterBlock.DoesNotExist:
            return Response(
                {"detail": f"Block {block_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

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
        except Exception as e:
            logger.exception("Analytics block fetch failed")
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        vo_list = _normalize_list(vo_raw)
        clf_list = _normalize_list(clf_raw)
        shg_list = _normalize_list(shg_raw)

        response = {
            "block_id": block_id,
            "block_name": block.block_name_en,
            "totals": {
                "total_vos": len(vo_list),
                "total_clfs": len(clf_list),
                "total_shgs": len(shg_list),
            },
        }

        if detail:
            response["village_wise"] = self._village_wise(
                block_id,
                vo_list,
                shg_list,
            )

        return Response(response)

    # ------------------------------------------------------------------
    # VILLAGE LEVEL ANALYTICS (DB-backed names)
    # ------------------------------------------------------------------

    def _village_wise(
        self,
        block_id: int,
        vo_list: List[Dict],
        shg_list: List[Dict],
    ):
        """
        Village-wise analytics using master_village as source of truth.
        """

        village_stats: Dict[int, Dict[str, Any]] = {}

        # ------------------------------------
        # 1. SHG → direct villageId mapping
        # ------------------------------------
        for shg in shg_list:
            village_id = shg.get("villageId")
            if not village_id:
                continue

            village_stats.setdefault(
                village_id,
                {
                    "village_id": village_id,
                    "village_name": None,
                    "total_shgs": 0,
                    "total_vos": 0,
                },
            )
            village_stats[village_id]["total_shgs"] += 1

        # ------------------------------------
        # 2. VO → Panchayat → Villages
        # ------------------------------------
        panchayat_ids = {
            vo.get("panchayatId")
            for vo in vo_list
            if vo.get("panchayatId")
        }

        if panchayat_ids:
            villages = (
                MasterVillage.objects
                .filter(
                    block_id=block_id,
                    panchayat_id__in=panchayat_ids,
                )
                .values("village_id")
            )

            for v in villages:
                vid = v["village_id"]
                village_stats.setdefault(
                    vid,
                    {
                        "village_id": vid,
                        "village_name": None,
                        "total_shgs": 0,
                        "total_vos": 0,
                    },
                )
                village_stats[vid]["total_vos"] += 1

        if not village_stats:
            return []

        # ------------------------------------
        # 3. Fetch village names (single query)
        # ------------------------------------
        village_names = {
            v.village_id: (v.village_name_english or v.village_name_local)
            for v in MasterVillage.objects.filter(
                village_id__in=village_stats.keys()
            )
        }

        for vid, stats in village_stats.items():
            stats["village_name"] = village_names.get(vid)

        return list(village_stats.values())
