# core/api/urls.py
from django.urls import path
from .lookups import *

urlpatterns = [
    # Districts
    path('districts/', DistrictListView.as_view(), name='district-list'),
    path('districts/<int:district_id>/', DistrictDetailView.as_view(), name='district-detail'),

    # Blocks (list supports ?district_id=, compatibility path kept)
    path('blocks/<int:district_id>/', BlockListView.as_view(), name='block-list'),
    path('blocks/', BlockListView.as_view(), name='block-list-canonical'),
    path('blocks/detail/<int:block_id>/', BlockDetailView.as_view(), name='block-detail'),

    # Panchayats
    path('panchayats/<int:block_id>/', PanchayatListView.as_view(), name='panchayat-list'),
    path('panchayats/', PanchayatListView.as_view(), name='panchayat-list-canonical'),
    path('panchayats/detail/<int:panchayat_id>/', PanchayatDetailView.as_view(), name='panchayat-detail'),

    # Villages
    path('villages/<int:panchayat_id>/', VillageListView.as_view(), name='village-list'),
    path('villages/', VillageListView.as_view(), name='village-list-canonical'),
    path('villages/detail/<int:village_id>/', VillageDetailView.as_view(), name='village-detail'),

    # SHGs
    path('shg-list/<int:block_id>/', ShgListByBlockView.as_view(), name='shg-list-by-block'),
    path('shg-list/by-district/<int:district_id>/', ShgListByBlockView.as_view(), name='shg-list-by-district'),
    path('shgs/', ShgListByBlockView.as_view(), name='shg-list-canonical'),
    path('shg-detail/<str:shg_code>/', ShgDetailView.as_view(), name='shg-detail'),

    # Beneficiaries (canonical)
    path('beneficiary-list/<str:shg_code>/', BeneficiaryListByShgView.as_view(), name='beneficiary-list'),
    path('beneficiaries/', BeneficiaryListByShgView.as_view(), name='beneficiaries-canonical'),
    path('beneficiary-detail/<str:member_code>/', BeneficiaryDetailView.as_view(), name='beneficiary-detail'),

    # CLF
    path('clf-list/', ClfListView.as_view(), name='clf-list'),
    path('clf-detail/<str:clf_code>/', ClfDetailView.as_view(), name='clf-detail'),
    path('members-under-clf/<str:clf_code>/', MembersUnderClfView.as_view(), name='members-under-clf'),
    path('panchayats-under-clf/<str:clf_code>/', PanchayatsUnderClfView.as_view(), name='panchayats-under-clf'),
    path('villages-under-clf/<str:clf_code>/', VillagesUnderClfView.as_view(), name='villages-under-clf'),

    # Roles / Users / State / Mandal
    path('roles/', MasterRolesView.as_view(), name='master-roles'),
    path('users/', MasterUserListView.as_view(), name='master-users'),
    path('states/', MasterStateView.as_view(), name='master-states'),
    path('mandals/', MasterMandalView.as_view(), name='master-mandals'),

    # Geo-scope of a user
    path('user-geoscope/<int:user_id>/', UserGeoScopeView.as_view(), name='user-geoscope'),
]
