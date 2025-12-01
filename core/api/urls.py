# core/api/urls.py

from django.urls import path

from .lookups import (
    DistrictListView,
    DistrictDetailView,
    BlockListView,
    BlockDetailView,
    PanchayatListView,
    PanchayatDetailView,
    VillageListView,
    VillageDetailView,
    ShgListByBlockView,
    ShgDetailView,
    BeneficiaryListByShgView,
    BeneficiaryDetailView,
    ClfListView,
    ClfDetailView,
    MembersUnderClfView,
    PanchayatsUnderClfView,
    VillagesUnderClfView,
)
from .upsrlm import (
    UpsrlmClfListView,
    UpsrlmClfDetailView,
    UpsrlmClfVoListView,
    UpsrlmClfPanchayatListView,
    UpsrlmClfMembersView,
    UpsrlmVoListView,
    UpsrlmVoDetailView,
    UpsrlmVoShgListView,
    UpsrlmVoMembersView,
)

app_name = "core_lookups"

urlpatterns = [
    # ----------------------------
    # Districts
    # ----------------------------
    path("districts/", DistrictListView.as_view(), name="district-list"),
    path(
        "districts/<int:district_id>/",
        DistrictDetailView.as_view(),
        name="district-detail",
    ),

    # ----------------------------
    # Blocks
    # ----------------------------
    path("blocks/", BlockListView.as_view(), name="block-list"),
    path(
        "blocks/<int:district_id>/",
        BlockListView.as_view(),
        name="block-list-by-district",
    ),
    path("blocks/detail/<int:block_id>/", BlockDetailView.as_view(), name="block-detail"),

    # ----------------------------
    # Panchayats
    # ----------------------------
    path("panchayats/", PanchayatListView.as_view(), name="panchayat-list"),
    path(
        "panchayats/<int:block_id>/",
        PanchayatListView.as_view(),
        name="panchayats-by-block",
    ),
    path(
        "panchayats/detail/<int:panchayat_id>/",
        PanchayatDetailView.as_view(),
        name="panchayat-detail",
    ),

    # ----------------------------
    # Villages
    # ----------------------------
    path("villages/", VillageListView.as_view(), name="village-list"),
    path(
        "villages/<int:panchayat_id>/",
        VillageListView.as_view(),
        name="villages-by-panchayat",
    ),
    path(
        "villages/detail/<int:village_id>/",
        VillageDetailView.as_view(),
        name="village-detail",
    ),

    # ----------------------------
    # SHGs (from master_shg_list table)
    # ----------------------------
    path(
        "shg-list/<int:block_id>/",
        ShgListByBlockView.as_view(),
        name="shg-list-by-block",
    ),
    path(
        "shg-detail/<str:shg_code>/",
        ShgDetailView.as_view(),
        name="shg-detail",
    ),
    path(
        "beneficiaries/<str:shg_code>/",
        BeneficiaryListByShgView.as_view(),
        name="beneficiaries-by-shg",
    ),
    path(
        "beneficiary-detail/<str:member_code>/",
        BeneficiaryDetailView.as_view(),
        name="beneficiary-detail",
    ),

    # ----------------------------
    # CLF list + detail + sublists
    # (from master_* CLF tables)
    # ----------------------------
    path("clf-list/", ClfListView.as_view(), name="clf-list"),
    path(
        "clf-detail/<str:clf_code>/",
        ClfDetailView.as_view(),
        name="clf-detail",
    ),
    path(
        "clf-members/<str:clf_code>/",
        MembersUnderClfView.as_view(),
        name="clf-members",
    ),
    path(
        "panchayats-under-clf/<str:clf_code>/",
        PanchayatsUnderClfView.as_view(),
        name="panchayats-under-clf",
    ),
    path(
        "villages-under-clf/<str:clf_code>/",
        VillagesUnderClfView.as_view(),
        name="villages-under-clf",
    ),

    # ============================================================
    # NEW: UPSRLM LokOS proxy endpoints (external APISetu calls)
    # ============================================================

    # CLF
    path(
        "upsrlm-clf-list/<int:block_id>/",
        UpsrlmClfListView.as_view(),
        name="upsrlm-clf-list",
    ),
    path(
        "upsrlm-clf-detail/<str:clf_code>/",
        UpsrlmClfDetailView.as_view(),
        name="upsrlm-clf-detail",
    ),
    path(
        "upsrlm-clf-vo/<str:clf_code>/",
        UpsrlmClfVoListView.as_view(),
        name="upsrlm-clf-vo",
    ),
    path(
        "upsrlm-panchayats-in-clf/<str:clf_code>/",
        UpsrlmClfPanchayatListView.as_view(),
        name="upsrlm-panchayats-in-clf",
    ),
    path(
        "upsrlm-clf-members/<str:clf_code>/",
        UpsrlmClfMembersView.as_view(),
        name="upsrlm-clf-members",
    ),

    # VO
    path(
        "upsrlm-vo-list/<int:block_id>/",
        UpsrlmVoListView.as_view(),
        name="upsrlm-vo-list",
    ),
    path(
        "upsrlm-vo-detail/<str:vo_code>/",
        UpsrlmVoDetailView.as_view(),
        name="upsrlm-vo-detail",
    ),
    path(
        "upsrlm-vo-shg/<str:vo_code>/",
        UpsrlmVoShgListView.as_view(),
        name="upsrlm-vo-shg",
    ),
    path(
        "upsrlm-vo-members/<str:vo_code>/",
        UpsrlmVoMembersView.as_view(),
        name="upsrlm-vo-members",
    ),
]
