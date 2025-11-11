# core/api/lookups.py
from rest_framework import permissions, generics, pagination
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from core.models import (
    MasterDistrict, MasterBlock, MasterPanchayat,
    MasterVillage, MasterShgList, MasterBeneficiary
)
from epSakhi.api.serializers import (
    MasterDistrictSerializer, MasterBlockSerializer,
    MasterPanchayatSerializer, MasterShgSerializer,
    MasterBeneficiarySerializer
)

CACHE_TTL = 300  # seconds (5 minutes)

class TenPerPagePagination(pagination.PageNumberPagination):
    """
    Fixed page size pagination: always 10 items per page.
    Does NOT allow changing page size via query params.
    """
    page_size = 10
    page_size_query_param = None
    max_page_size = 10

# ----------------------------
# Districts
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class DistrictListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterDistrictSerializer
    pagination_class = TenPerPagePagination

    def get_queryset(self):
        # Use select_related only if serializer accesses related fields; harmless otherwise.
        qs = MasterDistrict.objects.all().order_by('district_name_en').select_related('state', 'mandal')
        return qs

# ----------------------------
# Blocks by district
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class BlockListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterBlockSerializer
    pagination_class = TenPerPagePagination

    def get_queryset(self):
        district_id = self.kwargs.get('district_id')
        qs = MasterBlock.objects.filter(district_id=district_id).order_by('block_name_en').select_related('state', 'district')
        return qs

# ----------------------------
# Panchayats by block
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class PanchayatListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterPanchayatSerializer
    pagination_class = TenPerPagePagination

    def get_queryset(self):
        block_id = self.kwargs.get('block_id')
        qs = MasterPanchayat.objects.filter(block_id=block_id).order_by('panchayat_name_en').select_related('state', 'district', 'block')
        return qs

# ----------------------------
# Villages by panchayat (custom dict response, paginated)
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class VillageListView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    pagination_class = TenPerPagePagination

    def get(self, request, panchayat_id=None):
        qs = MasterVillage.objects.filter(panchayat_id=panchayat_id, is_active=True).order_by('village_name_english').select_related('state', 'district', 'block', 'panchayat')
        # Build lightweight dict list (same shape as before)
        data = [{'village_id': v.village_id, 'village_name': v.village_name_english, 'beneficiary_count': 0} for v in qs]

        # Paginate the list and return standard paginated response
        page = self.paginate_queryset(data)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(data)

# ----------------------------
# SHGs by village
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class ShgListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterShgSerializer
    pagination_class = TenPerPagePagination

    def get_queryset(self):
        village_id = self.kwargs.get('village_id')
        qs = MasterShgList.objects.filter(village_id=village_id).order_by('name').select_related('state', 'district', 'block', 'panchayat', 'village')
        return qs

# ----------------------------
# Beneficiaries by SHG
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class BeneficiaryListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterBeneficiarySerializer
    pagination_class = TenPerPagePagination

    def get_queryset(self):
        shg_code = self.kwargs.get('shg_code')
        qs = MasterBeneficiary.objects.filter(shg_code=shg_code).order_by('member_name').select_related('state', 'district', 'block', 'panchayat', 'village')
        return qs
