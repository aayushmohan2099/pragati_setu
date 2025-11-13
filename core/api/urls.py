# core/api/urls.py
from django.urls import path
from .lookups import (
    DistrictListView, BlockListView, PanchayatListView, VillageListView,
    ShgListByBlockView, ShgListByDistrictView, ShgDetailView,
    BeneficiaryListByShgView, BeneficiaryDetailView, BeneficiaryListByBlockView, BeneficiaryListByDistrictView,
    UserGeoScopeView
)

urlpatterns = [
    path('districts/', DistrictListView.as_view(), name='district-list'),
    path('blocks/<int:district_id>/', BlockListView.as_view(), name='block-list'),
    path('panchayats/<int:block_id>/', PanchayatListView.as_view(), name='panchayat-list'),
    path('villages/<int:panchayat_id>/', VillageListView.as_view(), name='village-list'),

    # SHG endpoints (paginated, 10 per page)
    # List SHGs by block id
    path('shg-list/<int:block_id>/', ShgListByBlockView.as_view(), name='shg-list-by-block'),
    # List SHGs by district id
    path('shg-list/by-district/<int:district_id>/', ShgListByDistrictView.as_view(), name='shg-list-by-district'),
    # SHG detail (combined)
    path('shg-detail/<str:shg_code>/', ShgDetailView.as_view(), name='shg-detail'),

    # Beneficiary endpoints
    path('beneficiary-list/<str:shg_code>/', BeneficiaryListByShgView.as_view(), name='beneficiary-list'),
    path('beneficiary-detail/<str:member_code>/', BeneficiaryDetailView.as_view(), name='beneficiary-detail'),
    path('beneficiaries/by-block/<int:block_id>/', BeneficiaryListByBlockView.as_view(), name='beneficiaries-by-block'),
    path('beneficiaries/by-district/<int:district_id>/', BeneficiaryListByDistrictView.as_view(), name='beneficiaries-by-district'),

    # Geo-scope of a user (which block/districts user can see)
    path('user-geoscope/<int:user_id>/', UserGeoScopeView.as_view(), name='user-geoscope'),
]
