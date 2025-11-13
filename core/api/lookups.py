# core/api/lookups.py
from rest_framework import permissions, generics, pagination
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Prefetch, Q
from django.core.paginator import Paginator

from core.models import (
    MasterDistrict, MasterBlock, MasterPanchayat,
    MasterVillage, MasterShgList, MasterShgAddresses,
    MasterShgBanks, MasterShgPhone, MasterBeneficiary,
    MasterBeneficiaryAddress, MasterBeneficiaryBank,
    MasterBeneficiaryDesignation, MasterBeneficiaryPhone,
    MasterGeoUserScope, MasterUser, MasterRoles
)
from epSakhi.api.serializers import (
    MasterDistrictSerializer, MasterBlockSerializer,
    MasterPanchayatSerializer, MasterShgListSerializer,
    MasterShgDetailSerializer, MasterBeneficiarySerializer
)

CACHE_TTL = 300  # seconds (5 minutes)

class TenPerPagePagination(pagination.PageNumberPagination):
    """
    Fixed page size pagination: always 10 items per page.
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
        qs = MasterVillage.objects.filter(panchayat_id=panchayat_id, is_active=True).order_by('village_name_english').select_related('state', 'district', 'block', 'panchayat').only('village_id', 'village_name_english')
        data = [{'village_id': v.village_id, 'village_name': v.village_name_english, 'beneficiary_count': 0} for v in qs]

        page = self.paginate_queryset(data)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(data)

# ----------------------------
# SHGs by BLOCK (paginated, 10/page)
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class ShgListByBlockView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterShgListSerializer
    pagination_class = TenPerPagePagination

    def get_queryset(self):
        block_id = self.kwargs.get('block_id')
        # select_related for FK fields, only to limit columns for speed
        qs = MasterShgList.objects.filter(block_id=block_id).order_by('name').select_related('state', 'district', 'block', 'panchayat', 'village').only('id', 'shg_code', 'name', 'block_id', 'district_id', 'village_id', 'is_active')
        return qs

# ----------------------------
# SHGs by DISTRICT (paginated)
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class ShgListByDistrictView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterShgListSerializer
    pagination_class = TenPerPagePagination

    def get_queryset(self):
        district_id = self.kwargs.get('district_id')
        qs = MasterShgList.objects.filter(district_id=district_id).order_by('name').select_related('state', 'district', 'block', 'panchayat', 'village').only('id', 'shg_code', 'name', 'block_id', 'district_id', 'village_id', 'is_active')
        return qs

# ----------------------------
# SHG DETAIL - combined data (addresses, banks, phones)
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class ShgDetailView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, shg_code=None):
        if not shg_code:
            return Response({'detail': 'shg_code required'}, status=400)
        try:
            shg = MasterShgList.objects.select_related('state', 'district', 'block', 'panchayat', 'village').only(
                'id', 'shg_code', 'name', 'formation_date', 'is_active', 'latitude', 'longitude',
                'block_id', 'district_id', 'panchayat_id', 'village_id'
            ).get(shg_code=shg_code)
        except MasterShgList.DoesNotExist:
            return Response({'detail': 'SHG not found'}, status=404)

        # gather related tables efficiently
        addresses = list(MasterShgAddresses.objects.filter(shg_code=shg_code).only('address_line1', 'address_line2', 'city_town', 'pincode', 'state_name', 'block_id', 'district_id', 'village', 'panchayat'))
        banks = list(MasterShgBanks.objects.filter(shg_code=shg_code).only('account_no', 'bank_name', 'ifsc_code', 'is_default'))
        phones = list(MasterShgPhone.objects.filter(shg_code=shg_code).only('phone_no', 'is_default'))

        # Use serializer to shape base shg data
        serializer = MasterShgDetailSerializer(shg)

        data = serializer.data
        # attach related lists as simple dicts
        data['addresses'] = [
            {
                'address_line1': a.address_line1,
                'address_line2': a.address_line2,
                'city_town': a.city_town,
                'pincode': a.pincode,
                'state_name': a.state_name
            } for a in addresses
        ]
        data['banks'] = [
            {
                'account_no': b.account_no,
                'bank_name': b.bank_name,
                'ifsc_code': b.ifsc_code,
                'is_default': b.is_default
            } for b in banks
        ]
        data['phones'] = [
            {
                'phone_no': p.phone_no,
                'is_default': p.is_default
            } for p in phones
        ]

        return Response(data)

# ----------------------------
# Beneficiaries by SHG (paginated)
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class BeneficiaryListByShgView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterBeneficiarySerializer
    pagination_class = TenPerPagePagination

    def get_queryset(self):
        shg_code = self.kwargs.get('shg_code')
        qs = MasterBeneficiary.objects.filter(shg_code=shg_code).order_by('member_name').select_related('state', 'district', 'block', 'panchayat', 'village').only('member_code', 'member_name', 'dob', 'gender', 'shg_code')
        return qs

# ----------------------------
# Beneficiary detail (combined)
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class BeneficiaryDetailView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, member_code=None):
        if not member_code:
            return Response({'detail': 'member_code required'}, status=400)
        try:
            mb = MasterBeneficiary.objects.select_related('state', 'district', 'block', 'panchayat', 'village').only(
                'member_code', 'member_name', 'dob', 'gender', 'joining_date', 'shg_code', 'state_id', 'district_id', 'block_id'
            ).get(member_code=member_code)
        except MasterBeneficiary.DoesNotExist:
            return Response({'detail': 'Beneficiary not found'}, status=404)

        addresses = list(MasterBeneficiaryAddress.objects.filter(member_code=member_code).only('address_line1', 'address_line2', 'address_type', 'city_town', 'postal_code'))
        banks = list(MasterBeneficiaryBank.objects.filter(member_code=member_code).only('account_no', 'ifsc_code', 'bank_name', 'is_default'))
        designations = list(MasterBeneficiaryDesignation.objects.filter(member_code=member_code).only('designation', 'is_signatory', 'member_name'))
        phones = list(MasterBeneficiaryPhone.objects.filter(member_code=member_code).only('phone_no', 'is_default'))

        # Basic serializer for beneficiary
        from epSakhi.api.serializers import MasterBeneficiaryDetailSerializer
        serializer = MasterBeneficiaryDetailSerializer(mb)

        data = serializer.data
        data['addresses'] = [
            {
                'address_line1': a.address_line1,
                'address_line2': a.address_line2,
                'address_type': a.address_type,
                'city_town': a.city_town,
                'postal_code': a.postal_code
            } for a in addresses
        ]
        data['banks'] = [
            {
                'account_no': b.account_no,
                'ifsc_code': b.ifsc_code,
                'bank_name': b.bank_name,
                'is_default': b.is_default
            } for b in banks
        ]
        data['designations'] = [
            {'designation': d.designation, 'is_signatory': d.is_signatory, 'member_name': d.member_name} for d in designations
        ]
        data['phones'] = [
            {'phone_no': p.phone_no, 'is_default': p.is_default} for p in phones
        ]
        return Response(data)

# ----------------------------
# Beneficiaries by BLOCK
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class BeneficiaryListByBlockView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterBeneficiarySerializer
    pagination_class = TenPerPagePagination

    def get_queryset(self):
        block_id = self.kwargs.get('block_id')
        qs = MasterBeneficiary.objects.filter(block_id=block_id).order_by('member_name').select_related('state', 'district', 'block', 'panchayat', 'village').only('member_code', 'member_name', 'dob', 'gender', 'shg_code')
        return qs

# ----------------------------
# Beneficiaries by DISTRICT
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class BeneficiaryListByDistrictView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterBeneficiarySerializer
    pagination_class = TenPerPagePagination

    def get_queryset(self):
        district_id = self.kwargs.get('district_id')
        qs = MasterBeneficiary.objects.filter(district_id=district_id).order_by('member_name').select_related('state', 'district', 'block', 'panchayat', 'village').only('member_code', 'member_name', 'dob', 'gender', 'shg_code')
        return qs

# ----------------------------
# User GeoScope - which blocks/districts a user can see
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class UserGeoScopeView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, user_id=None):
        if user_id is None:
            return Response({'detail': 'user_id required'}, status=400)

        # Find master user and role
        try:
            mu = MasterUser.objects.select_related('role').only('id', 'username', 'role_id').get(id=user_id)
            role_name = mu.get_role_name() or ''
        except MasterUser.DoesNotExist:
            return Response({'detail': 'User not found'}, status=404)

        # Fetch geoscopes rows for this user (may be multiple)
        scopes = MasterGeoUserScope.objects.filter(user_id=user_id, is_active=1).only('block_id', 'district_id')

        blocks = set()
        districts = set()
        for s in scopes:
            if s.block_id:
                blocks.add(int(s.block_id))
            if s.district_id:
                districts.add(int(s.district_id))

        # Role-driven logic: some roles are block-level (bmmu), others district-level (dmmu, dcnrlm, dc)
        # We'll shape the response accordingly.
        role_name_lower = (role_name or '').lower()
        response = {'user_id': user_id, 'username': mu.username, 'role': role_name, 'blocks': [], 'districts': []}

        # Roles that manage blocks (bmmu type)
        if role_name_lower.startswith('bmmu') or role_name_lower == 'bmmu':
            response['blocks'] = sorted(list(blocks))
        # Roles that manage districts
        elif role_name_lower.startswith('dmmu') or role_name_lower in ('dmmu', 'dc', 'dcnrlm', 'dcnrlm'):
            response['districts'] = sorted(list(districts))
        else:
            # default: include both if present
            response['blocks'] = sorted(list(blocks))
            response['districts'] = sorted(list(districts))

        return Response(response)
