# core/api/urls.py
from django.urls import path
from .lookups import DistrictListView, BlockListView, PanchayatListView, VillageListView, ShgListView, BeneficiaryListView

urlpatterns = [
    path('districts/', DistrictListView.as_view(), name='district-list'),
    path('blocks/<int:district_id>/', BlockListView.as_view(), name='block-list'),
    path('panchayats/<int:block_id>/', PanchayatListView.as_view(), name='panchayat-list'),
    path('villages/<int:panchayat_id>/', VillageListView.as_view(), name='village-list'),
    path('shgs/<int:village_id>/', ShgListView.as_view(), name='shg-list'),
    path('beneficiaries/<str:shg_code>/', BeneficiaryListView.as_view(), name='beneficiary-list'),
]
