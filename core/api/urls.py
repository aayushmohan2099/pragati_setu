from django.urls import path
from .lookups import (
    DistrictListView, BlockListView, PanchayatListView, VillageListView,
    ShgListByBlockView, ShgDetailView,
    BeneficiaryListByShgView, BeneficiaryDetailView, BeneficiaryListByBlockView, BeneficiaryListByDistrictView,
    UserGeoScopeView,
    ClfListView, ClfDetailView, MembersUnderClfView, PanchayatsUnderClfView, VillagesUnderClfView,
    MasterRolesView, MasterUserListView, MasterStateView, MasterMandalView
)

urlpatterns = [
    # ---------- existing geographic endpoints (enhanced, backward compatible) ----------
    path('districts/', DistrictListView.as_view(), name='district-list'),
    path('blocks/<int:district_id>/', BlockListView.as_view(), name='block-list'),
    # optional query-based blocks: GET /api/v1/lookups/blocks/?district_id=...
    path('panchayats/<int:block_id>/', PanchayatListView.as_view(), name='panchayat-list'),
    # optional query-based panchayats: GET /api/v1/lookups/panchayats/?block_id=...
    path('villages/<int:panchayat_id>/', VillageListView.as_view(), name='village-list'),
    # optional query-based villages: GET /api/v1/lookups/villages/?panchayat_id=...

    # ---------- SHG endpoints ----------
    # backward-compatible path that previously existed (list SHGs by block id)
    path('shg-list/<int:block_id>/', ShgListByBlockView.as_view(), name='shg-list-by-block'),
    # backward-compatible path by district (kept)
    path('shg-list/by-district/<int:district_id>/', ShgListByBlockView.as_view(), name='shg-list-by-district'),
    # canonical query-based SHG list: GET /api/v1/lookups/shgs/?block_id=...&village_id=...
    path('shgs/', ShgListByBlockView.as_view(), name='shg-list-canonical'),
    # SHG detail (combined)
    path('shg-detail/<str:shg_code>/', ShgDetailView.as_view(), name='shg-detail'),

    # ---------- Beneficiary endpoints (unified) ----------
    # backward-compatible list by shg_code (kept)
    path('beneficiary-list/<str:shg_code>/', BeneficiaryListByShgView.as_view(), name='beneficiary-list'),
    # canonical (query-based) list of beneficiaries:
    path('beneficiaries/', BeneficiaryListByShgView.as_view(), name='beneficiaries-canonical'),
    # detail
    path('beneficiary-detail/<str:member_code>/', BeneficiaryDetailView.as_view(), name='beneficiary-detail'),
    # compatibility endpoints
    path('beneficiaries/by-block/<int:block_id>/', BeneficiaryListByBlockView.as_view(), name='beneficiaries-by-block'),
    path('beneficiaries/by-district/<int:district_id>/', BeneficiaryListByDistrictView.as_view(), name='beneficiaries-by-district'),

    # ---------- CLF endpoints ----------
    path('clf-list/', ClfListView.as_view(), name='clf-list'),
    path('clf-detail/<str:clf_code>/', ClfDetailView.as_view(), name='clf-detail'),
    path('members-under-clf/<str:clf_code>/', MembersUnderClfView.as_view(), name='members-under-clf'),
    path('panchayats-under-clf/<str:clf_code>/', PanchayatsUnderClfView.as_view(), name='panchayats-under-clf'),
    path('villages-under-clf/<str:clf_code>/', VillagesUnderClfView.as_view(), name='villages-under-clf'),

    # ---------- Roles / Users / State / Mandal ----------
    path('roles/', MasterRolesView.as_view(), name='master-roles'),
    path('users/', MasterUserListView.as_view(), name='master-users'),
    path('states/', MasterStateView.as_view(), name='master-states'),
    path('mandals/', MasterMandalView.as_view(), name='master-mandals'),

    # ---------- Geo-scope of a user ----------
    path('user-geoscope/<int:user_id>/', UserGeoScopeView.as_view(), name='user-geoscope'),
]
