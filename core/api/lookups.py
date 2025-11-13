"""
core/api/lookups.py

Enhanced lookups with:
- multi-filter support
- search (comma-separated tokens)
- group_by (single or comma-separated)
- ordering (supports 'age' computed from dob)
- pagination: page, page_size (PageNumberPagination)
- DB optimizations: select_related, prefetch_related, only
- caching decorator preserved

"""

from rest_framework import permissions, generics, pagination, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Prefetch, Q, Count, F, IntegerField
from django.db.models.functions import ExtractYear, Now
from django.core.paginator import Paginator
from django.conf import settings

from core.models import (
    MasterDistrict, MasterBlock, MasterPanchayat,
    MasterVillage, MasterShgList, MasterShgAddresses,
    MasterShgBanks, MasterShgPhone, MasterBeneficiary,
    MasterBeneficiaryAddress, MasterBeneficiaryBank,
    MasterBeneficiaryDesignation, MasterBeneficiaryPhone,
    MasterClfList, MasterClfAddresses, MasterClfBanks,
    MasterClfPhones, MasterClfVoDetails,
    MasterMembersUnderClf, MasterPanchayatsUnderClf, MasterVillagesUnderClf,
    MasterGeoUserScope, MasterUser, MasterRoles, MasterState, MasterMandal
)

from core.api.serializers import (
    MasterDistrictSerializer, MasterBlockSerializer,
    MasterPanchayatSerializer, MasterShgListSerializer,
    MasterShgDetailSerializer, MasterBeneficiarySerializer,
    MasterBeneficiaryDetailSerializer, MasterClfDetailSerializer,
    MasterClfListSerializer, MasterClfAddressesSerializer,
    MasterClfBanksSerializer, MasterClfPhonesSerializer, MasterClfVoDetailsSerializer,
    MasterMembersUnderClfSerializer, MasterPanchayatsUnderClfSerializer, MasterVillagesUnderClfSerializer,
    MasterStateSerializer, MasterMandalSerializer, MasterUserSerializer, MasterRolesSerializer,
    MasterVillageSerializer, MasterGeoUserScopeSerializer
)

# Cache TTL seconds (default 300)
CACHE_TTL = getattr(settings, 'CACHE_TTL', 300)

# PageNumber pagination with client-settable page_size (bounded)
class FlexiblePagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

# --------------------------
# Helper utilities
# --------------------------
def parse_csv_param(val):
    """Split comma-separated query param into a list of trimmed tokens."""
    if not val:
        return []
    return [p.strip() for p in val.split(',') if p.strip()]

def apply_search(qs, request, search_fields):
    """
    Apply 'search' query param.
    Behavior:
      - request.GET['search'] may contain comma-separated tokens: token1,token2
      - For each token, build a Q object that ORs across search_fields.
      - Then AND all token-Qs together (so all tokens must match somewhere).
    """
    search_raw = request.GET.get('search', '').strip()
    if not search_raw or not search_fields:
        return qs
    tokens = parse_csv_param(search_raw)
    if not tokens:
        return qs
    q_total = Q()
    for token in tokens:
        q_token = Q()
        for f in search_fields:
            q_token |= Q(**{f + '__icontains': token})
        q_total &= q_token
    return qs.filter(q_total)

def apply_filters(qs, request, allowed_filters):
    """
    allowed_filters: dict mapping query_param -> model_field_name (or lambda for complex)
    Example: {'district_id': 'district_id', 'is_active':'is_active'}
    Supports multiple filters; if query_param has comma-separated values, treat as IN.
    """
    for param, field in allowed_filters.items():
        val = request.GET.get(param, None)
        if val is None or val == '':
            continue
        # allow comma-separated multiple values -> IN
        tokens = parse_csv_param(val)
        if len(tokens) == 1:
            qs = qs.filter(**{field: tokens[0]})
        else:
            qs = qs.filter(**{f"{field}__in": tokens})
    # Range filters (created_from/created_to) handled separately by callers if needed
    return qs

def apply_ordering(qs, request, allowed_ordering, annotate_age=False):
    """
    allowed_ordering: set/list of allowed ordering fields (string names).
    Supports 'age' which must be annotated by caller (or annotate_age True will annotate).
    ordering param: ordering=<field> or ordering=-<field>
    """
    ord_raw = request.GET.get('ordering', '').strip()
    if not ord_raw:
        return qs
    # support comma-separated ordering: take first only (to keep simple and safe)
    ord_field = parse_csv_param(ord_raw)[0]
    desc = ord_field.startswith('-')
    field_name = ord_field[1:] if desc else ord_field
    if field_name == 'age':
        # annotate approximate age = ExtractYear(Now()) - ExtractYear(dob)
        # Use ExtractYear for DB-side calculation
        qs = qs.annotate(age=(ExtractYear(Now()) - ExtractYear('dob')))
        # allowed
        order_expr = '-age' if desc else 'age'
        return qs.order_by(order_expr)
    if field_name not in allowed_ordering:
        return qs
    order_expr = ('-' + field_name) if desc else field_name
    return qs.order_by(order_expr)

def apply_group_by(qs, request, allowed_group_by, id_field='id'):
    """
    group_by: comma-separated allowed fields. For now we support single-field grouping primarily.
    Returns dict with 'group_by' info if requested, else None.
    If include_items=true, include items per group (paginated).
    """
    group_raw = request.GET.get('group_by', '').strip()
    if not group_raw:
        return None
    groups = parse_csv_param(group_raw)
    # restrict to first allowed grouping for now (safe & efficient)
    group_field = None
    for g in groups:
        if g in allowed_group_by:
            group_field = g
            break
    if not group_field:
        return None

    include_items = request.GET.get('include_items', 'false').lower() in ('1', 'true', 'yes')
    # Build values() group
    agg = qs.values(group_field).annotate(count=Count(id_field)).order_by('-count')
    result = {'group_by': group_field, 'groups': []}
    # If include_items true, collect items for that group (bounded)
    for bucket in agg:
        key = bucket.get(group_field)
        count = bucket.get('count')
        group_entry = {'key': key, 'count': count}
        if include_items:
            # fetch items in that group (limit page_size to avoid huge payloads)
            items_qs = qs.filter(**{group_field: key}).order_by()[:50]
            # use serializer-agnostic representation: model __dict__ via values()
            item_list = list(items_qs.values())
            group_entry['items'] = item_list
        result['groups'].append(group_entry)
    return result

def apply_field_projection(request, queryset):
    """
    If ?fields=col1,col2 passed, limit the queryset using .only() for related objects
    and return a values() when necessary in lists. We will respect fields param for lists.
    """
    fields_raw = request.GET.get('fields', '').strip()
    if not fields_raw:
        return queryset
    fields = parse_csv_param(fields_raw)
    # For ORM QuerySet, .only works for model fields; prefer .values to easily return dicts.
    return queryset.values(*fields)


# ----------------------------
# Districts (existing endpoint - enhanced)
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class DistrictListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterDistrictSerializer
    pagination_class = FlexiblePagination

    # Allowed operations
    SEARCH_FIELDS = ['district_name_en', 'district_name_local']
    ALLOWED_FILTERS = {
        'state_id': 'state_id',
        'mandal_id': 'mandal_id',
        'is_active': 'is_active'
    }
    ALLOWED_ORDERING = {'district_id', 'district_name_en', 'created_at', 'updated_at'}
    ALLOWED_GROUP_BY = {'state_id', 'mandal_id'}

    def get_queryset(self):
        qs = MasterDistrict.objects.all().select_related('state', 'mandal').order_by('district_name_en')
        # apply filters/search/ordering
        qs = apply_filters(qs, self.request, self.ALLOWED_FILTERS)
        qs = apply_search(qs, self.request, self.SEARCH_FIELDS)
        qs = apply_ordering(qs, self.request, self.ALLOWED_ORDERING)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        grouped = apply_group_by(qs, request, self.ALLOWED_GROUP_BY, id_field='district_id')
        if grouped:
            return Response(grouped)

        # optional fields projection
        fields = request.GET.get('fields')
        if fields:
            qs = qs.values(*parse_csv_param(fields))
            page = self.paginate_queryset(qs)
            return self.get_paginated_response(list(page) if page is not None else list(qs))
        return super().list(request, *args, **kwargs)


# ----------------------------
# Blocks by district (existing route preserved, enhanced)
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class BlockListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterBlockSerializer
    pagination_class = FlexiblePagination

    SEARCH_FIELDS = ['block_name_en']
    ALLOWED_FILTERS = {
        'district_id': 'district_id',  # user's change: search by block_id primary; keep district filter also
        'state_id': 'state_id',
        'is_aspirational': 'is_aspirational'
    }
    ALLOWED_ORDERING = {'block_id', 'block_name_en', 'is_aspirational', 'created_at'}
    ALLOWED_GROUP_BY = {'state_id', 'district_id', 'is_aspirational'}

    def get_queryset(self):
        # preserve existing behaviour: if district_id path param present, filter by it
        district_id = self.kwargs.get('district_id')
        qs = MasterBlock.objects.all().select_related('state', 'district').order_by('block_name_en')
        if district_id:
            qs = qs.filter(district_id=district_id)
        qs = apply_filters(qs, self.request, self.ALLOWED_FILTERS)
        qs = apply_search(qs, self.request, self.SEARCH_FIELDS)
        qs = apply_ordering(qs, self.request, self.ALLOWED_ORDERING)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        grouped = apply_group_by(qs, request, self.ALLOWED_GROUP_BY, id_field='block_id')
        if grouped:
            return Response(grouped)

        fields = request.GET.get('fields')
        if fields:
            qs = qs.values(*parse_csv_param(fields))
            page = self.paginate_queryset(qs)
            return self.get_paginated_response(list(page) if page is not None else list(qs))
        return super().list(request, *args, **kwargs)


# ----------------------------
# Panchayats by block (existing)
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class PanchayatListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterPanchayatSerializer
    pagination_class = FlexiblePagination

    SEARCH_FIELDS = ['panchayat_name_en']
    ALLOWED_FILTERS = {
        'block_id': 'block_id',
        'district_id': 'district_id',
        'state_id': 'state_id'
    }
    ALLOWED_ORDERING = {'panchayat_id', 'panchayat_name_en', 'created_at'}
    ALLOWED_GROUP_BY = {'block_id', 'district_id'}

    def get_queryset(self):
        block_id = self.kwargs.get('block_id')
        qs = MasterPanchayat.objects.all().select_related('state', 'district', 'block').order_by('panchayat_name_en')
        if block_id:
            qs = qs.filter(block_id=block_id)
        qs = apply_filters(qs, self.request, self.ALLOWED_FILTERS)
        qs = apply_search(qs, self.request, self.SEARCH_FIELDS)
        qs = apply_ordering(qs, self.request, self.ALLOWED_ORDERING)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        grouped = apply_group_by(qs, request, self.ALLOWED_GROUP_BY, id_field='panchayat_id')
        if grouped:
            return Response(grouped)
        fields = request.GET.get('fields')
        if fields:
            qs = qs.values(*parse_csv_param(fields))
            page = self.paginate_queryset(qs)
            return self.get_paginated_response(list(page) if page is not None else list(qs))
        return super().list(request, *args, **kwargs)


# ----------------------------
# Villages by panchayat (existing)
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class VillageListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterVillageSerializer
    pagination_class = FlexiblePagination

    SEARCH_FIELDS = ['village_name_english']
    ALLOWED_FILTERS = {
        'panchayat_id': 'panchayat_id',
        'block_id': 'block_id',
        'district_id': 'district_id',
        'is_active': 'is_active'
    }
    ALLOWED_ORDERING = {'village_id', 'village_name_english', 'created_at'}
    ALLOWED_GROUP_BY = {'block_id', 'is_active'}

    def get_queryset(self):
        panchayat_id = self.kwargs.get('panchayat_id')
        qs = MasterVillage.objects.all().select_related('state', 'district', 'block', 'panchayat').order_by('village_name_english')
        if panchayat_id:
            qs = qs.filter(panchayat_id=panchayat_id)
        qs = apply_filters(qs, self.request, self.ALLOWED_FILTERS)
        qs = apply_search(qs, self.request, self.SEARCH_FIELDS)
        qs = apply_ordering(qs, self.request, self.ALLOWED_ORDERING)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        grouped = apply_group_by(qs, request, self.ALLOWED_GROUP_BY, id_field='village_id')
        if grouped:
            return Response(grouped)
        fields = request.GET.get('fields')
        if fields:
            qs = qs.values(*parse_csv_param(fields))
            page = self.paginate_queryset(qs)
            return self.get_paginated_response(list(page) if page is not None else list(qs))
        return super().list(request, *args, **kwargs)


# ----------------------------
# SHGs - unified endpoint
# Old endpoints kept (shg-list/<block_id>/ and by-district) remain compatible.
# New canonical endpoint: /api/v1/lookups/shgs/?block_id=...&district_id=...&village_id=...
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class ShgListByBlockView(generics.ListAPIView):
    """
    This class now acts as the unified SHG list endpoint:
    - If block_id/district_id/village_id query params provided they filter accordingly.
    - Keeps existing path param block_id if present (backwards-compatible).
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterShgListSerializer
    pagination_class = FlexiblePagination

    SEARCH_FIELDS = ['name', 'shg_code', 'nic_code']
    ALLOWED_FILTERS = {
        'block_id': 'block_id',
        'district_id': 'district_id',
        'village_id': 'village_id',
        'panchayat_id': 'panchayat_id',
        'state_id': 'state_id',
        'is_active': 'is_active',
        'pfms_verified': 'pfms_verified',
        'is_complete': 'is_complete'
    }
    ALLOWED_ORDERING = {'id', 'name', 'formation_date', 'is_active'}
    # user requested adding group by village_id and panchayat_id
    ALLOWED_GROUP_BY = {'block_id', 'district_id', 'village_id', 'panchayat_id', 'is_active'}

    def get_queryset(self):
        # Start base qs with related data to optimize list serialization
        qs = MasterShgList.objects.all().select_related('state', 'district', 'block', 'panchayat', 'village').order_by('name')
        # path param block_id (compatibility)
        path_block = self.kwargs.get('block_id')
        if path_block:
            qs = qs.filter(block_id=path_block)
        # apply filters from query params (supports multiple together)
        qs = apply_filters(qs, self.request, self.ALLOWED_FILTERS)
        qs = apply_search(qs, self.request, self.SEARCH_FIELDS)
        qs = apply_ordering(qs, self.request, self.ALLOWED_ORDERING)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        grouped = apply_group_by(qs, request, self.ALLOWED_GROUP_BY, id_field='id')
        if grouped:
            return Response(grouped)

        fields = request.GET.get('fields')
        if fields:
            qs = qs.values(*parse_csv_param(fields))
            page = self.paginate_queryset(qs)
            return self.get_paginated_response(list(page) if page is not None else list(qs))
        return super().list(request, *args, **kwargs)


# ----------------------------
# SHG DETAIL (combined) preserved, optimized and uses serializer
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class ShgDetailView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, shg_code=None):
        if not shg_code:
            return Response({'detail': 'shg_code required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            shg = MasterShgList.objects.select_related('state', 'district', 'block', 'panchayat', 'village').get(shg_code=shg_code)
        except MasterShgList.DoesNotExist:
            return Response({'detail': 'SHG not found'}, status=status.HTTP_404_NOT_FOUND)

        # Fetch related sets optimized with .only()
        addresses_qs = MasterShgAddresses.objects.filter(shg_code=shg_code).only('address_line1','address_line2','city_town','pincode','state_name','block_id','district_id','village','panchayat')
        banks_qs = MasterShgBanks.objects.filter(shg_code=shg_code).only('account_no','bank_name','ifsc_code','is_default')
        phones_qs = MasterShgPhone.objects.filter(shg_code=shg_code).only('phone_no','is_default')

        serializer = MasterShgDetailSerializer({
            'shg': shg,
            'addresses': list(addresses_qs),
            'banks': list(banks_qs),
            'phones': list(phones_qs)
        })
        return Response(serializer.data)


# ----------------------------
# Beneficiaries - unified endpoint
# Old endpoints kept as compatibility wrappers.
# New canonical: /api/v1/lookups/beneficiaries/?shg_code=...&block_id=...&village_id=...&... or member_code for detail
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class BeneficiaryListByShgView(generics.ListAPIView):
    """
    Unified beneficiary endpoint:
     - If 'member_code' query param provided -> return detail (combined).
     - Otherwise return list filtered by provided params (supports multiple filters).
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterBeneficiarySerializer
    pagination_class = FlexiblePagination

    SEARCH_FIELDS = ['member_name', 'member_code', 'nic_member_code', 'father_husband']
    ALLOWED_FILTERS = {
        'shg_code': 'shg_code',
        'block_id': 'block_id',
        'district_id': 'district_id',
        'village_id': 'village_id',
        'panchayat_id': 'panchayat_id',
        'state_id': 'state_id',
        'marital_status': 'marital_status',
        'religion': 'religion',
        'social_category': 'social_category',
        'aadhar_verified': 'aadhar_verified'
    }
    # ordering includes 'age' as requested
    ALLOWED_ORDERING = {'member_name', 'member_code', 'dob', 'joining_date', 'age'}
    ALLOWED_GROUP_BY = {'shg_code', 'block_id', 'district_id', 'village_id', 'panchayat_id', 'gender', 'marital_status', 'religion', 'social_category'}

    def get_queryset(self):
        # base qs
        qs = MasterBeneficiary.objects.all().select_related('state', 'district', 'block', 'panchayat', 'village').order_by('member_name')
        # apply filters & search
        qs = apply_filters(qs, self.request, self.ALLOWED_FILTERS)
        qs = apply_search(qs, self.request, self.SEARCH_FIELDS)
        # ordering including 'age'
        qs = apply_ordering(qs, self.request, self.ALLOWED_ORDERING, annotate_age=True)
        return qs

    def list(self, request, *args, **kwargs):
        member_code = request.GET.get('member_code') or self.kwargs.get('shg_code') and None
        # If member_code provided -> return combined detail via BeneficiaryDetailView behaviour
        if member_code:
            # reuse BeneficiaryDetailView logic
            from .lookups import BeneficiaryDetailView  # safe import within func to avoid circular
            return BeneficiaryDetailView().get(request, member_code=member_code)

        qs = self.get_queryset()
        grouped = apply_group_by(qs, request, self.ALLOWED_GROUP_BY, id_field='member_code')
        if grouped:
            return Response(grouped)

        fields = request.GET.get('fields')
        if fields:
            qs = qs.values(*parse_csv_param(fields))
            page = self.paginate_queryset(qs)
            return self.get_paginated_response(list(page) if page is not None else list(qs))
        return super().list(request, *args, **kwargs)


# ----------------------------
# Beneficiary detail (combined)
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class BeneficiaryDetailView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, member_code=None):
        # member_code may come in URL or query param
        member_code = member_code or request.GET.get('member_code')
        if not member_code:
            return Response({'detail': 'member_code required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            mb = MasterBeneficiary.objects.select_related('state', 'district', 'block', 'panchayat', 'village').get(member_code=member_code)
        except MasterBeneficiary.DoesNotExist:
            return Response({'detail': 'Beneficiary not found'}, status=status.HTTP_404_NOT_FOUND)

        addresses = MasterBeneficiaryAddress.objects.filter(member_code=member_code).only('address_line1','address_line2','address_type','city_town','postal_code')
        banks = MasterBeneficiaryBank.objects.filter(member_code=member_code).only('account_no','ifsc_code','bank_name','is_default')
        designations = MasterBeneficiaryDesignation.objects.filter(member_code=member_code).only('designation','is_signatory','member_name')
        phones = MasterBeneficiaryPhone.objects.filter(member_code=member_code).only('phone_no','is_default')

        serializer = MasterBeneficiaryDetailSerializer({
            'beneficiary': mb,
            'addresses': list(addresses),
            'banks': list(banks),
            'designations': list(designations),
            'phones': list(phones)
        })
        return Response(serializer.data)


# ----------------------------
# Beneficiaries by block & district endpoints (compatibility)
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class BeneficiaryListByBlockView(BeneficiaryListByShgView):
    def get(self, request, block_id=None):
        # if block_id path param provided, ensure filter is applied and call list
        if block_id:
            # inject into GET by creating a mutable QueryDict is messy; instead call get_queryset directly
            self.kwargs['block_id'] = block_id
            # fallback: filter in queryset by block_id
            qs = self.get_queryset().filter(block_id=block_id)
            # follow parent list implementation
            grouped = apply_group_by(qs, request, self.ALLOWED_GROUP_BY, id_field='member_code')
            if grouped:
                return Response(grouped)
            fields = request.GET.get('fields')
            if fields:
                qs = qs.values(*parse_csv_param(fields))
                page = self.paginate_queryset(qs)
                return self.get_paginated_response(list(page) if page is not None else list(qs))
            page = self.paginate_queryset(qs)
            return self.get_paginated_response(page)
        return super().get(request)

@method_decorator(cache_page(CACHE_TTL), name='get')
class BeneficiaryListByDistrictView(BeneficiaryListByShgView):
    def get(self, request, district_id=None):
        if district_id:
            qs = self.get_queryset().filter(district_id=district_id)
            grouped = apply_group_by(qs, request, self.ALLOWED_GROUP_BY, id_field='member_code')
            if grouped:
                return Response(grouped)
            fields = request.GET.get('fields')
            if fields:
                qs = qs.values(*parse_csv_param(fields))
                page = self.paginate_queryset(qs)
                return self.get_paginated_response(list(page) if page is not None else list(qs))
            page = self.paginate_queryset(qs)
            return self.get_paginated_response(page)
        return super().get(request)


# ----------------------------
# CLF endpoints and detail
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class ClfListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterClfListSerializer
    pagination_class = FlexiblePagination

    SEARCH_FIELDS = ['name', 'clf_code', 'nic_code']
    ALLOWED_FILTERS = {
        'state_id': 'state_id',
        'district_id': 'district_id',
        'block_id': 'block_id',
        'pfms_verified': 'pfms_verified',
        'is_complete': 'is_complete'
    }
    ALLOWED_ORDERING = {'id', 'name', 'formation_date', 'created_date'}
    ALLOWED_GROUP_BY = {'district_id', 'block_id', 'pfms_verified', 'is_complete'}

    def get_queryset(self):
        qs = MasterClfList.objects.all().select_related('state', 'district', 'block').order_by('name')
        qs = apply_filters(qs, self.request, self.ALLOWED_FILTERS)
        qs = apply_search(qs, self.request, self.SEARCH_FIELDS)
        qs = apply_ordering(qs, self.request, self.ALLOWED_ORDERING)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        grouped = apply_group_by(qs, request, self.ALLOWED_GROUP_BY, id_field='id')
        if grouped:
            return Response(grouped)
        fields = request.GET.get('fields')
        if fields:
            qs = qs.values(*parse_csv_param(fields))
            page = self.paginate_queryset(qs)
            return self.get_paginated_response(list(page) if page is not None else list(qs))
        return super().list(request, *args, **kwargs)


@method_decorator(cache_page(CACHE_TTL), name='get')
class ClfDetailView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, clf_code=None):
        if not clf_code:
            return Response({'detail': 'clf_code required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            clf = MasterClfList.objects.select_related('state', 'district', 'block').get(clf_code=clf_code)
        except MasterClfList.DoesNotExist:
            return Response({'detail': 'CLF not found'}, status=status.HTTP_404_NOT_FOUND)

        addresses = MasterClfAddresses.objects.filter(clf_code=clf_code).only('address_line1','address_line2','city_town','postal_code')
        banks = MasterClfBanks.objects.filter(clf_code=clf_code).only('account_no','bank_name','ifsc_code','is_default')
        phones = MasterClfPhones.objects.filter(clf_code=clf_code).only('phone_no','is_default')
        vo_details = MasterClfVoDetails.objects.filter(clf_code=clf_code).only('vo_code','vo_name','vo_formation_date')

        serializer = MasterClfDetailSerializer({
            'clf': clf,
            'addresses': list(addresses),
            'banks': list(banks),
            'phones': list(phones),
            'vo_details': list(vo_details)
        })
        return Response(serializer.data)


# ----------------------------
# CLF-members / panchayats / villages under CLF
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class MembersUnderClfView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterMembersUnderClfSerializer
    pagination_class = FlexiblePagination

    SEARCH_FIELDS = ['member_name', 'designation']
    ALLOWED_FILTERS = {
        'clf_code': 'clf_code',
        'is_signatory': 'is_signatory'
    }
    ALLOWED_ORDERING = {'member_name', 'designation'}
    ALLOWED_GROUP_BY = {'designation', 'is_signatory'}

    def get_queryset(self):
        clf_code = self.kwargs.get('clf_code') or self.request.GET.get('clf_code')
        qs = MasterMembersUnderClf.objects.all().order_by('member_name')
        if clf_code:
            qs = qs.filter(clf_code=clf_code)
        qs = apply_filters(qs, self.request, self.ALLOWED_FILTERS)
        qs = apply_search(qs, self.request, self.SEARCH_FIELDS)
        qs = apply_ordering(qs, self.request, self.ALLOWED_ORDERING)
        return qs


@method_decorator(cache_page(CACHE_TTL), name='get')
class PanchayatsUnderClfView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterPanchayatsUnderClfSerializer
    pagination_class = FlexiblePagination

    SEARCH_FIELDS = ['panchayat_name', 'panchayat_code']
    ALLOWED_FILTERS = {'clf_code': 'clf_code'}
    ALLOWED_ORDERING = {'panchayat_name'}
    ALLOWED_GROUP_BY = {'panchayat'}

    def get_queryset(self):
        clf_code = self.kwargs.get('clf_code') or self.request.GET.get('clf_code')
        qs = MasterPanchayatsUnderClf.objects.all().select_related('panchayat')
        if clf_code:
            qs = qs.filter(clf_code=clf_code)
        qs = apply_filters(qs, self.request, self.ALLOWED_FILTERS)
        qs = apply_search(qs, self.request, self.SEARCH_FIELDS)
        qs = apply_ordering(qs, self.request, self.ALLOWED_ORDERING)
        return qs


@method_decorator(cache_page(CACHE_TTL), name='get')
class VillagesUnderClfView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterVillagesUnderClfSerializer
    pagination_class = FlexiblePagination

    SEARCH_FIELDS = ['village_name', 'village_code']
    ALLOWED_FILTERS = {'clf_code': 'clf_code'}
    ALLOWED_ORDERING = {'village_name'}
    ALLOWED_GROUP_BY = {'village'}

    def get_queryset(self):
        clf_code = self.kwargs.get('clf_code') or self.request.GET.get('clf_code')
        qs = MasterVillagesUnderClf.objects.all().select_related('village', 'panchayat')
        if clf_code:
            qs = qs.filter(clf_code=clf_code)
        qs = apply_filters(qs, self.request, self.ALLOWED_FILTERS)
        qs = apply_search(qs, self.request, self.SEARCH_FIELDS)
        qs = apply_ordering(qs, self.request, self.ALLOWED_ORDERING)
        return qs


# ----------------------------
# Geo scope of a user - preserved and enhanced using serializer
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class UserGeoScopeView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, user_id=None):
        if user_id is None:
            return Response({'detail': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            mu = MasterUser.objects.select_related('role').get(id=user_id)
            role_name = mu.get_role_name() or ''
        except MasterUser.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        scopes = MasterGeoUserScope.objects.filter(user_id=user_id, is_active=1)
        blocks = sorted({int(s.block_id) for s in scopes if s.block_id})
        districts = sorted({int(s.district_id) for s in scopes if s.district_id})

        role_name_lower = (role_name or '').lower()
        response = {'user_id': user_id, 'username': mu.username, 'role': role_name, 'blocks': [], 'districts': []}
        if role_name_lower.startswith('bmmu') or role_name_lower == 'bmmu':
            response['blocks'] = blocks
        elif role_name_lower.startswith('dmmu') or role_name_lower in ('dmmu', 'dc', 'dcnrlm'):
            response['districts'] = districts
        else:
            response['blocks'] = blocks
            response['districts'] = districts

        return Response(response)


# ----------------------------
# Additional small list endpoints for roles, users, states, mandals
# ----------------------------
@method_decorator(cache_page(CACHE_TTL), name='get')
class MasterRolesView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterRolesSerializer
    pagination_class = FlexiblePagination

    SEARCH_FIELDS = ['name', 'role_type']
    ALLOWED_FILTERS = {'role_type': 'role_type'}
    ALLOWED_ORDERING = {'id', 'name', 'created_at', 'updated_at'}
    ALLOWED_GROUP_BY = {'role_type'}

    def get_queryset(self):
        qs = MasterRoles.objects.all().order_by('id')
        qs = apply_filters(qs, self.request, self.ALLOWED_FILTERS)
        qs = apply_search(qs, self.request, self.SEARCH_FIELDS)
        qs = apply_ordering(qs, self.request, self.ALLOWED_ORDERING)
        return qs


@method_decorator(cache_page(CACHE_TTL), name='get')
class MasterUserListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterUserSerializer
    pagination_class = FlexiblePagination

    SEARCH_FIELDS = ['username', 'recovery_mobile', 'TH_urid']
    ALLOWED_FILTERS = {'role_id': 'role_id', 'is_active': 'is_active'}
    ALLOWED_ORDERING = {'id', 'username', 'last_active_on', 'created_at', 'updated_at'}
    ALLOWED_GROUP_BY = {'role_id', 'is_active'}

    def get_queryset(self):
        qs = MasterUser.objects.all().select_related('role').order_by('username')
        qs = apply_filters(qs, self.request, self.ALLOWED_FILTERS)
        qs = apply_search(qs, self.request, self.SEARCH_FIELDS)
        qs = apply_ordering(qs, self.request, self.ALLOWED_ORDERING)
        return qs


@method_decorator(cache_page(CACHE_TTL), name='get')
class MasterStateView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterStateSerializer
    pagination_class = FlexiblePagination

    SEARCH_FIELDS = ['state_name_en', 'state_name_local', 'state_short_name_en']
    ALLOWED_FILTERS = {'category': 'category', 'is_active': 'is_active'}
    ALLOWED_ORDERING = {'state_id', 'state_name_en', 'created_at'}
    ALLOWED_GROUP_BY = {'category', 'is_active'}

    def get_queryset(self):
        qs = MasterState.objects.all().order_by('state_name_en')
        qs = apply_filters(qs, self.request, self.ALLOWED_FILTERS)
        qs = apply_search(qs, self.request, self.SEARCH_FIELDS)
        qs = apply_ordering(qs, self.request, self.ALLOWED_ORDERING)
        return qs


@method_decorator(cache_page(CACHE_TTL), name='get')
class MasterMandalView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = MasterMandalSerializer
    pagination_class = FlexiblePagination

    SEARCH_FIELDS = ['name', 'th_urid']
    ALLOWED_FILTERS = {'created_by': 'created_by'}
    ALLOWED_ORDERING = {'id', 'name', 'created_at'}
    ALLOWED_GROUP_BY = {'created_by'}

    def get_queryset(self):
        qs = MasterMandal.objects.all().select_related('created_by').order_by('name')
        qs = apply_filters(qs, self.request, self.ALLOWED_FILTERS)
        qs = apply_search(qs, self.request, self.SEARCH_FIELDS)
        qs = apply_ordering(qs, self.request, self.ALLOWED_ORDERING)
        return qs
