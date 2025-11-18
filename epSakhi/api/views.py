import requests
import json
import csv
from io import StringIO
from collections import defaultdict

from django.conf import settings
from django.core.cache import cache
from django.db import transaction, models
from django.db.models import Q, Prefetch, F, OuterRef, Subquery
from django.http import StreamingHttpResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets, status, filters, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from core.models import (
    MasterUser,
    MasterPanchayat,
)
from epSakhi.models import (
    CRPEP,
    BeneficiaryRecorded,
    ExistingEnterprise,
    NewEnterprise,
    EnterpriseLoanDetail,
    EnterpriseSupportDetail,
    EnterpriseTrainingReq,
    EnterpriseMedia,
    CRPEPToPanchayat,
)
from .serializers import (
    CRPEPSerializer,
    BeneficiaryRecordedSerializer,
    ExistingEnterpriseSerializer,
    NewEnterpriseSerializer,
    EnterpriseLoanDetailSerializer,
    EnterpriseSupportDetailSerializer,
    EnterpriseTrainingReqSerializer,
    EnterpriseMediaSerializer,
)

# cache ttl in seconds
CACHE_TTL = getattr(settings, 'CACHE_TTL', 60 * 5)
SHG_CACHE_TTL = getattr(settings, 'SHG_CACHE_TTL', 60 * 5)  # default 5 minutes


class BaseProjectionMixin:
    """
    Allows list endpoints to accept ?fields=col1,col2 and return .values(...) directly (fast).
    """

    def apply_fields_projection(self, request, qs):
        fields = request.GET.get('fields')
        if not fields:
            return qs
        cols = [f.strip() for f in fields.split(',') if f.strip()]
        if not cols:
            return qs
        return qs.values(*cols)


# -------------------------------------------------------------------
# Small generic helpers for list-style endpoints
# -------------------------------------------------------------------

def _parse_csv_param(value):
    if not value:
        return []
    return [v.strip() for v in str(value).split(',') if v.strip()]


def _paginate_plain_list(request, items):
    """
    For list-of-dict style responses with:
      ?page (1-based), ?page_size (default 10, max 100).
    """
    try:
        page = int(request.GET.get('page', '1'))
        page_size = min(100, int(request.GET.get('page_size', '10')))
    except Exception:
        page, page_size = 1, 10

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    data = items[start:end]
    return {
        'meta': {'page': page, 'page_size': page_size, 'total': total},
        'data': data,
    }


def _apply_list_filters(items, filter_map, params):
    """
    filter_map: { query_param_name -> item_key }
    params: request.GET
    """
    for qparam, key in filter_map.items():
        raw_val = params.get(qparam)
        if raw_val is None:
            continue
        vals = _parse_csv_param(raw_val)
        if not vals:
            continue
        vals_set = {str(v) for v in vals}
        items = [row for row in items if str(row.get(key)) in vals_set]
    return items


def _apply_list_search(items, search_param, search_fields):
    if not search_param:
        return items
    q = search_param.lower()

    def _match(row):
        for f in search_fields:
            val = row.get(f)
            if val is not None and q in str(val).lower():
                return True
        return False

    return [row for row in items if _match(row)]


def _apply_list_ordering(items, ordering_param, allowed_fields):
    if not ordering_param:
        return items
    orderings = _parse_csv_param(ordering_param)
    if not orderings:
        return items
    first = orderings[0]
    desc = first.startswith('-')
    field = first[1:] if desc else first
    if field not in allowed_fields:
        return items

    def key_fn(row):
        v = row.get(field)
        return '' if v is None else v

    return sorted(items, key=key_fn, reverse=desc)


def _apply_list_group_by(items, group_by_param):
    """
    Returns aggregated list of {<group fields...>, count}
    or None if no group_by requested.
    """
    if not group_by_param:
        return None
    keys = [k.strip() for k in str(group_by_param).split(',') if k.strip()]
    if not keys:
        return None

    counts = defaultdict(int)
    for row in items:
        gkey = tuple(row.get(k) for k in keys)
        counts[gkey] += 1

    out = []
    for gkey, count in counts.items():
        obj = {keys[i]: gkey[i] for i in range(len(keys))}
        obj['count'] = count
        out.append(obj)
    return out


def _apply_fields_projection_list(items, fields_param):
    if not fields_param:
        return items
    cols = [c.strip() for c in str(fields_param).split(',') if c.strip()]
    if not cols:
        return items
    projected = []
    for row in items:
        projected.append({c: row.get(c) for c in cols})
    return projected


# -------------------------------------------------------------------
# Helper to call APISETU for SHG
# -------------------------------------------------------------------

def _call_apisetu_shg_list(block_id):
    url = settings.APISETU_SHG_LIST_URL_TEMPLATE.format(block_id=block_id)
    headers = {
        'X-APISETU-CLIENTID': settings.APISETU_CLIENT_ID,
        'X-APISETU-APIKEY': settings.APISETU_API_KEY,
        'accept': 'application/json'
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _call_apisetu_shg_detail(shg_code):
    url = settings.APISETU_SHG_DETAIL_URL_TEMPLATE.format(shg_code=shg_code)
    headers = {
        'X-APISETU-CLIENTID': settings.APISETU_CLIENT_ID,
        'X-APISETU-APIKEY': settings.APISETU_API_KEY,
        'accept': 'application/json'
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


# -------------------------------------------------------------------
# UPSRLM SHG proxy endpoints (already existing)
# -------------------------------------------------------------------

class UpsrlmShgListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, block_id):
        # fetch or read cached JSON for block_id
        cache_key = f"upsrlm_shg_list:{block_id}"
        j = cache.get(cache_key)
        if j is None:
            try:
                j = _call_apisetu_shg_list(block_id)
            except Exception as e:
                return Response({'detail': f'Error fetching remote shg-list: {str(e)}'}, status=502)
            cache.set(cache_key, j, SHG_CACHE_TTL)

        queryset = j  # list of dicts

        # Filters: panchayat_id, village_id, shgType, specialShg, social_category
        p_panchayat = request.GET.get('panchayat_id')
        p_village = request.GET.get('village_id')
        p_shgtype = request.GET.get('shgType')
        p_special = request.GET.get('specialShg')
        p_social = request.GET.get('social_category')
        if p_panchayat:
            queryset = [x for x in queryset if str(x.get('panchayatId')) == str(p_panchayat)]
        if p_village:
            queryset = [x for x in queryset if str(x.get('villageId')) == str(p_village)]
        if p_shgtype:
            queryset = [x for x in queryset if x.get('shgType') == p_shgtype]
        if p_special is not None:
            val = p_special in ('1', 'true', 'True')
            queryset = [x for x in queryset if bool(int(x.get('specialShg', 0))) == val]
        if p_social:
            queryset = [x for x in queryset if x.get('socialCategory') == p_social]

        # Search: name, nic_code, shg_code
        q = request.GET.get('search')
        if q:
            ql = q.lower()

            def matches(item):
                return (
                    ql in (str(item.get('name', '')).lower())
                    or ql in (str(item.get('nicCode', '')).lower())
                    or ql in (str(item.get('code', '')).lower())
                )

            queryset = [x for x in queryset if matches(x)]

        # Ordering: formation_date (-asc,-dsc)
        ordering = request.GET.get('ordering')
        if ordering:
            reverse = ordering.startswith('-')
            def key_fn(it):
                return it.get('formationDate') or ''
            queryset = sorted(queryset, key=key_fn, reverse=reverse)

        # group_by (aggregation)
        group_by = request.GET.get('group_by')
        if group_by:
            keys = [k.strip() for k in group_by.split(',') if k.strip()]
            agg = {}
            for it in queryset:
                group_key = tuple(str(it.get(k)) for k in keys)
                agg[group_key] = agg.get(group_key, 0) + 1
            out = []
            for k, cnt in agg.items():
                out.append({'group': dict(zip(keys, k)), 'count': cnt})
            return Response(out)

        # fields projection
        fields = request.GET.get('fields')
        if fields:
            cols = [c.strip() for c in fields.split(',') if c.strip()]
            queryset = [
                {c: (it.get(c) or it.get(c[0].lower() + c[1:], None)) for c in cols}
                for it in queryset
            ]

        # pagination
        result = _paginate_plain_list(request, queryset)
        return Response(result)


class UpsrlmShgMembersView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, shg_code):
        cache_key = f"upsrlm_shg_detail:{shg_code}"
        j = cache.get(cache_key)
        if j is None:
            try:
                j = _call_apisetu_shg_detail(shg_code)
            except Exception as e:
                return Response({'detail': f'Error fetching shg-detail: {str(e)}'}, status=502)
            cache.set(cache_key, j, SHG_CACHE_TTL)

        members = j.get('shg_members', [])

        # filters: aadhar_verified, gender, religion, social_category, designation
        if 'aadhar_verified' in request.GET:
            av = request.GET.get('aadhar_verified') in ('1', 'true', 'True')
            members = [m for m in members if bool(m.get('aadhar_verified')) == av]
        for f in ('gender', 'religion', 'social_category'):
            if request.GET.get(f):
                members = [m for m in members if m.get(f) == request.GET.get(f)]
        if request.GET.get('designation'):
            des = request.GET.get('designation')
            members = [m for m in members if any(d.get('designation') == des for d in m.get('member_designations', []))]

        # search
        q = request.GET.get('search')
        if q:
            ql = q.lower()

            def mmatch(m):
                if ql in (m.get('member_name') or '').lower():
                    return True
                if ql in (str(m.get('member_code')) or '').lower():
                    return True
                if ql in (m.get('nic_member_code') or '').lower():
                    return True
                if ql in (m.get('member_guid') or '').lower():
                    return True
                for ph in m.get('member_phones', []):
                    if ql in str(ph.get('phone_no') or ''):
                        return True
                return False

            members = [m for m in members if mmatch(m)]

        # ordering
        ordering = request.GET.get('ordering')
        if ordering:
            reverse = ordering.startswith('-')
            key = ordering.lstrip('-')
            members = sorted(members, key=lambda m: m.get(key) or '', reverse=reverse)

        # group_by
        group_by = request.GET.get('group_by')
        if group_by:
            keys = [k.strip() for k in group_by.split(',') if k.strip()]
            agg = {}
            for it in members:
                group_key = tuple(str(it.get(k)) for k in keys)
                agg[group_key] = agg.get(group_key, 0) + 1
            out = [{'group': dict(zip(keys, k)), 'count': v} for k, v in agg.items()]
            return Response(out)

        # fields projection
        fields = request.GET.get('fields')
        if fields:
            cols = [c.strip() for c in fields.split(',') if c.strip()]
            members = [{c: m.get(c) for c in cols} for m in members]

        # pagination
        result = _paginate_plain_list(request, members)
        return Response(result)


class UpsrlmShgDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, shg_code):
        cache_key = f"upsrlm_shg_detail:{shg_code}"
        j = cache.get(cache_key)
        if j is None:
            try:
                j = _call_apisetu_shg_detail(shg_code)
            except Exception as e:
                return Response({'detail': f'Error fetching shg-detail: {str(e)}'}, status=502)
            cache.set(cache_key, j, SHG_CACHE_TTL)

        data = {k: v for k, v in j.items() if k != 'shg_members'}
        fields = request.GET.get('fields')
        if fields:
            cols = [c.strip() for c in fields.split(',') if c.strip()]
            data = {c: data.get(c) for c in cols}
        return Response(data)


# -------------------------------------------------------------------
# Existing CRPEP ViewSet
# -------------------------------------------------------------------

class CRPEPViewSet(viewsets.ModelViewSet, BaseProjectionMixin):
    queryset = CRPEP.objects.all()
    serializer_class = CRPEPSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'mobile_number']
    ordering_fields = ['id', 'created_at']

    def get_queryset(self):
        """
        Base queryset optimized: restrict columns and eager-load real relations only.
        Note: district_id/block_id/panchayat_id are plain integer fields (NOT FKs).
        """
        qs = CRPEP.objects.select_related('master_user').only(
            'id',
            'name',
            'mobile_number',
            'category',
            'subcategory',
            'marks_obtained',
            'TH_urid',
            'district_id',
            'block_id',
            'panchayat_id',
            'lokos_shg_code',
            'lokos_member_code',
            'master_user_id',
            'nodal_clf',
            'created_at',
            'updated_at',
            'deleted_at',
        ).all().order_by('-id')

        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            try:
                mu = MasterUser.objects.filter(username=user.username).first()
                if mu:
                    role_name = None
                    try:
                        role_name = mu.get_role_name()
                    except Exception:
                        role_name = getattr(mu, 'role_name', None) or getattr(mu, 'role', None)
                    if role_name == 'crp_ep' or (
                        getattr(mu, 'role', None)
                        and getattr(getattr(mu, 'role'), 'id', None)
                        and role_name == 'crp_ep'
                    ):
                        qs = qs.filter(master_user_id=mu.id)
            except Exception:
                pass

        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        try:
            projected = self.apply_fields_projection(request, qs)
        except Exception:
            projected = qs

        is_values_qs = hasattr(projected, 'query') and getattr(projected.query, 'is_values', False)
        if isinstance(projected, list) or is_values_qs:
            page = self.paginate_queryset(projected)
            if page is not None:
                return self.get_paginated_response(list(page))
            return Response(list(projected))

        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(CACHE_TTL))
    def mylist(self, request):
        qs = self.get_queryset()
        try:
            projected = self.apply_fields_projection(request, qs)
        except Exception:
            projected = qs

        is_values_qs = hasattr(projected, 'query') and getattr(projected.query, 'is_values', False)
        if is_values_qs:
            page = self.paginate_queryset(projected)
            return self.get_paginated_response(list(page) if page is not None else list(projected))

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = CRPEPSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CRPEPSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def export(self, request):
        qs = self.get_queryset().only(
            'id',
            'name',
            'district_id',
            'block_id',
            'panchayat_id',
            'lokos_shg_code',
            'mobile_number',
            'category',
            'marks_obtained',
        )

        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ['id', 'name', 'district_id', 'block_id', 'panchayat_id', 'shg_code', 'mobile_number', 'category', 'marks_obtained']
        )

        for r in qs.iterator():
            writer.writerow(
                [
                    r.id,
                    r.name,
                    r.district_id,
                    r.block_id,
                    r.panchayat_id,
                    getattr(r, 'lokos_shg_code', ''),
                    r.mobile_number,
                    r.category,
                    r.marks_obtained,
                ]
            )

        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="crpep_export.csv"'
        return response


class CRPPanchayatMappingViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def link(self, request, pk=None):
        crp_id = pk
        panchayat_ids = request.data.get('panchayat_ids', [])
        if not isinstance(panchayat_ids, list):
            return Response({'detail': 'panchayat_ids must be list'}, status=status.HTTP_400_BAD_REQUEST)
        created = []
        with transaction.atomic():
            for pid in panchayat_ids:
                obj, _ = CRPEPToPanchayat.objects.get_or_create(crp_id=crp_id, allocated_panchayat_id=pid)
                created.append(obj.id)
        return Response({'created_ids': created})


# -------------------------------------------------------------------
# BeneficiaryRecorded ViewSet (existing)
# -------------------------------------------------------------------

class BeneficiaryRecordedViewSet(viewsets.ModelViewSet, BaseProjectionMixin):
    queryset = BeneficiaryRecorded.objects.all().order_by('-created_at')
    serializer_class = BeneficiaryRecordedSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['applicant_name', 'lokos_member_code', 'mobile', 'email', 'enterprise_id']
    ordering_fields = ['age', 'created_at']

    def get_queryset(self):
        qs = BeneficiaryRecorded.objects.all().order_by('-created_at')
        params = self.request.GET
        if params.get('district_id'):
            qs = qs.filter(district_id=int(params.get('district_id')))
        if params.get('block_id'):
            qs = qs.filter(block_id=int(params.get('block_id')))
        if params.get('panchayat_id'):
            qs = qs.filter(panchayat_id=int(params.get('panchayat_id')))
        if params.get('village_id'):
            qs = qs.filter(village_id=int(params.get('village_id')))
        if params.get('lokos_shg_code'):
            qs = qs.filter(lokos_shg_code=params.get('lokos_shg_code'))
        if params.get('gender'):
            qs = qs.filter(gender=params.get('gender'))
        if params.get('marital_status'):
            qs = qs.filter(marital_status=params.get('marital_status'))
        if params.get('category'):
            qs = qs.filter(category=params.get('category'))
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        group_by = request.GET.get('group_by')
        if group_by:
            keys = [k.strip() for k in group_by.split(',') if k.strip()]
            vals = qs.values(*keys).order_by().annotate(count=models.Count('TH_urid'))
            return Response(list(vals))

        fields = request.GET.get('fields')
        if fields:
            cols = [c.strip() for c in fields.split(',') if c.strip()]
            qs = qs.values(*cols)
            page = self.paginate_queryset(qs)
            return self.get_paginated_response(list(page) if page is not None else list(qs))
        return super().list(request, *args, **kwargs)


# -------------------------------------------------------------------
# Enterprise viewsets (existing)
# -------------------------------------------------------------------

class ExistingEnterpriseViewSet(viewsets.ModelViewSet):
    """
    /api/v1/epsakhi/existing-enterprise/

    NOTE (Option B):
    - This viewset now only handles the main ExistingEnterprise table.
    - Child tables (loan details, support detail, training reqs, media)
      are handled via separate CRUD APIs:
        * /enterprise-loan-details/
        * /enterprise-support-details/
        * /enterprise-training-reqs/
        * /enterprise-media/
    """
    queryset = ExistingEnterprise.objects.all().order_by('-created_at')
    serializer_class = ExistingEnterpriseSerializer
    permission_classes = [IsAuthenticated]


class NewEnterpriseViewSet(viewsets.ModelViewSet):
    """
    /api/v1/epsakhi/new-enterprise/
    """
    queryset = NewEnterprise.objects.all().order_by('-created_at')
    serializer_class = NewEnterpriseSerializer
    permission_classes = [IsAuthenticated]


# -------------------------------------------------------------------
# NEW: Separate CRUD APIs for child tables (Option B)
# -------------------------------------------------------------------

class EnterpriseLoanDetailViewSet(viewsets.ModelViewSet):
    """
    /api/v1/epsakhi/enterprise-loan-details/

    Query params:
      - enterprise_id=<TH_urid of ExistingEnterprise>  (optional filter)
    """
    queryset = EnterpriseLoanDetail.objects.all().order_by('-created_at')
    serializer_class = EnterpriseLoanDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        enterprise_id = self.request.query_params.get('enterprise_id')
        if enterprise_id:
            qs = qs.filter(enterprise_id=enterprise_id)
        return qs


class EnterpriseSupportDetailViewSet(viewsets.ModelViewSet):
    """
    /api/v1/epsakhi/enterprise-support-details/

    One enterprise can have MANY support_detail rows now.
    Filter by ?enterprise_id= to get all for one enterprise.
    """
    queryset = EnterpriseSupportDetail.objects.all().order_by('-created_at')
    serializer_class = EnterpriseSupportDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        enterprise_id = self.request.query_params.get('enterprise_id')
        if enterprise_id:
            qs = qs.filter(enterprise_id=enterprise_id)
        return qs


class EnterpriseTrainingReqViewSet(viewsets.ModelViewSet):
    """
    /api/v1/epsakhi/enterprise-training-reqs/

    One enterprise can have MANY training_req rows.
    Filter by ?enterprise_id=
    """
    queryset = EnterpriseTrainingReq.objects.all().order_by('-created_at')
    serializer_class = EnterpriseTrainingReqSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        enterprise_id = self.request.query_params.get('enterprise_id')
        if enterprise_id:
            qs = qs.filter(enterprise_id=enterprise_id)
        return qs


class EnterpriseMediaViewSet(viewsets.ModelViewSet):
    """
    /api/v1/epsakhi/enterprise-media/

    One enterprise can have MANY media rows. Each row can carry up to 1 file
    per field (photo_entrepreneur, photo_enterprise, open_box_photo, etc).

    IMPORTANT:
    - This endpoint accepts multipart/form-data.
    - RN frontend must send FormData with fields:
        enterprise_id: <TH_urid>
        photo_entrepreneur: (file)
        photo_enterprise: (file)
        open_box_photo: (file)
        close_box_photo: (file)
        others: (file)
        certificates: (file)
      Any missing fields can be omitted.
    """
    queryset = EnterpriseMedia.objects.all().order_by('-created_at')
    serializer_class = EnterpriseMediaSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        qs = super().get_queryset()
        enterprise_id = self.request.query_params.get('enterprise_id')
        if enterprise_id:
            qs = qs.filter(enterprise_id=enterprise_id)
        return qs


# ===================================================================
# NEW epSakhi APIs (non-"upsrlm-") with Search/Filter/Sort/Group/Fields
# ===================================================================

# 1) crp-list/<clf_code>
class CRPListByClfView(APIView):
    """
    GET /api/v1/epsakhi/crp-list/<clf_code>/

    - Lists selective fields of CRPEP for given nodal_clf (clf_code).
    - Default returned fields:
        id, name, lokos_shg_code, lokos_member_code,
        category, subcategory, mobile_number, marks_obtained

    Supports:
      - page, page_size
      - filters: district_id, block_id, panchayat_id
      - search: name, lokos_member_code, lokos_shg_code, mobile_number
      - ordering: id, name, marks_obtained, created_at
      - group_by: district_id, block_id, panchayat_id
      - fields: projection of any available columns
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, clf_code):
        # Base queryset
        qs = CRPEP.objects.filter(nodal_clf=clf_code)

        # Role-based restriction: if CRP logged in, only themselves
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            mu = MasterUser.objects.filter(username=user.username).first()
            if mu:
                try:
                    role_name = mu.get_role_name()
                except Exception:
                    role_name = getattr(mu, 'role_name', None) or getattr(mu, 'role', None)
                if role_name == 'crp_ep':
                    qs = qs.filter(master_user_id=mu.id)

        rows = list(
            qs.values(
                'id',
                'name',
                'lokos_shg_code',
                'lokos_member_code',
                'category',
                'subcategory',
                'mobile_number',
                'marks_obtained',
                'district_id',
                'block_id',
                'panchayat_id',
                'created_at',
            )
        )

        # Filters
        filter_map = {
            'district_id': 'district_id',
            'block_id': 'block_id',
            'panchayat_id': 'panchayat_id',
        }
        rows = _apply_list_filters(rows, filter_map, request.GET)

        # Search
        rows = _apply_list_search(
            rows,
            request.GET.get('search'),
            ['name', 'lokos_member_code', 'lokos_shg_code', 'mobile_number'],
        )

        # Ordering
        rows = _apply_list_ordering(
            rows,
            request.GET.get('ordering'),
            allowed_fields={'id', 'name', 'marks_obtained', 'created_at'},
        )

        # Grouping
        grouped = _apply_list_group_by(rows, request.GET.get('group_by'))
        if grouped is not None:
            grouped = _apply_fields_projection_list(grouped, request.GET.get('fields'))
            return Response(grouped)

        # Fields projection (default subset if not provided)
        fields_param = request.GET.get('fields')
        if fields_param:
            rows = _apply_fields_projection_list(rows, fields_param)
        else:
            rows = [
                {
                    'id': r['id'],
                    'name': r['name'],
                    'lokos_shg_code': r['lokos_shg_code'],
                    'lokos_member_code': r['lokos_member_code'],
                    'category': r['category'],
                    'subcategory': r['subcategory'],
                    'mobile_number': r['mobile_number'],
                    'marks_obtained': r['marks_obtained'],
                }
                for r in rows
            ]

        result = _paginate_plain_list(request, rows)
        return Response(result)


# 2) crp-detail/<member_code>
class CRPDetailView(APIView):
    """
    GET /api/v1/epsakhi/crp-detail/<member_code>/

    - member_code is matched with CRPEP.lokos_member_code.
    - Returns ALL fields of CRPEP (via serializer) for that CRP.
    - Supports:
        ?fields=field1,field2 (top-level CRPEP fields only).
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, member_code):
        crp = CRPEP.objects.filter(lokos_member_code=member_code).first()
        if not crp:
            return Response({'detail': 'CRP not found for given member_code'}, status=status.HTTP_404_NOT_FOUND)

        data = CRPEPSerializer(crp).data

        fields_param = request.GET.get('fields')
        if fields_param:
            cols = _parse_csv_param(fields_param)
            data = {k: v for k, v in data.items() if k in cols}

        return Response(data)

class CRPDetailbyUserID(APIView):
    """
    GET /api/v1/epsakhi/crp-detail/id/<id>/

    - <id> is matched with CRPEP.master_user_id.
    - Returns ALL fields of CRPEP (via serializer) for that CRP.
    - Supports:
        ?fields=field1,field2 (top-level CRPEP fields only).
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, id):
        # id comes from URL: /crp-detail/id/<id>/
        try:
            user_id = int(id)
        except (TypeError, ValueError):
            return Response({'detail': 'Invalid user id'}, status=status.HTTP_400_BAD_REQUEST)

        crp = CRPEP.objects.filter(master_user_id=user_id).first()
        if not crp:
            return Response(
                {'detail': 'CRP not found for given User ID'},
                status=status.HTTP_404_NOT_FOUND
            )

        data = CRPEPSerializer(crp).data

        fields_param = request.GET.get('fields')
        if fields_param:
            cols = _parse_csv_param(fields_param)
            data = {k: v for k, v in data.items() if k in cols}

        return Response(data)     

# 3) panchayats-under-crp/<member_code>
class CRPPanchayatsUnderCrpView(APIView):
    """
    GET /api/v1/epsakhi/panchayats-under-crp/<member_code>/

    - member_code = lokos_member_code for CRP (CRPEP.lokos_member_code).
    - DATA NOTE: mapping table epSakhi_crpep_panchayat.crp_id actually stores
                 CRPEP.master_user_id (user id), not CRPEP.id.
    - So we resolve CRPEP(s) by lokos_member_code, take their master_user_id,
      and then use those as crp_id in CRPEPToPanchayat.

    Default returned fields:
      panchayat_id, panchayat_name_en, block_id, district_id, state_id

    Supports:
      - page, page_size
      - filters: block_id, district_id, state_id
      - search: panchayat_name_en, panchayat_name_local, panchayat_code
      - ordering: panchayat_id, panchayat_name_en
      - group_by: block_id, district_id
      - fields: projection
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, member_code):
        # All CRPEP rows with this member_code
        crp_qs = CRPEP.objects.filter(lokos_member_code=member_code)
        if not crp_qs.exists():
            return Response(
                {'detail': 'CRP not found for given member_code'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # These are MasterUser IDs (user ids) – these are what crp_id stores in mapping table
        user_ids = list(
            crp_qs.values_list('master_user_id', flat=True)
        )
        user_ids = [u for u in user_ids if u is not None]
        if not user_ids:
            # CRP exists but not linked to any user_id / mapping
            rows = []
        else:
            panchayat_ids = list(
                CRPEPToPanchayat.objects.filter(
                    crp_id__in=user_ids  # IMPORTANT: mapping uses master_user_id semantics
                ).values_list('allocated_panchayat_id', flat=True)
            )

            if not panchayat_ids:
                rows = []
            else:
                qs = MasterPanchayat.objects.filter(panchayat_id__in=panchayat_ids).only(
                    'panchayat_id',
                    'panchayat_name_en',
                    'panchayat_name_local',
                    'panchayat_code',
                    'block_id',
                    'district_id',
                    'state_id',
                )
                rows = list(
                    qs.values(
                        'panchayat_id',
                        'panchayat_name_en',
                        'panchayat_name_local',
                        'panchayat_code',
                        'block_id',
                        'district_id',
                        'state_id',
                    )
                )

        # Filters
        filter_map = {
            'block_id': 'block_id',
            'district_id': 'district_id',
            'state_id': 'state_id',
        }
        rows = _apply_list_filters(rows, filter_map, request.GET)

        # Search
        rows = _apply_list_search(
            rows,
            request.GET.get('search'),
            ['panchayat_name_en', 'panchayat_name_local', 'panchayat_code'],
        )

        # Ordering
        rows = _apply_list_ordering(
            rows,
            request.GET.get('ordering'),
            allowed_fields={'panchayat_id', 'panchayat_name_en'},
        )

        # Grouping
        grouped = _apply_list_group_by(rows, request.GET.get('group_by'))
        if grouped is not None:
            grouped = _apply_fields_projection_list(grouped, request.GET.get('fields'))
            return Response(grouped)

        # Fields projection (default subset)
        fields_param = request.GET.get('fields')
        if fields_param:
            rows = _apply_fields_projection_list(rows, fields_param)
        else:
            rows = [
                {
                    'panchayat_id': r['panchayat_id'],
                    'panchayat_name_en': r['panchayat_name_en'],
                    'block_id': r['block_id'],
                    'district_id': r['district_id'],
                    'state_id': r['state_id'],
                }
                for r in rows
            ]

        result = _paginate_plain_list(request, rows)
        return Response(result)


class CRPPanchayatsUnderCrpByID(APIView):
    """
    GET /api/v1/epsakhi/panchayats-under-crp/id/<id>/

    - <id> is the MasterUser.id (user id) of the CRP.
    - DATA NOTE: epSakhi_crpep_panchayat.crp_id stores this user id
                 (CRPEP.master_user_id), not CRPEP.id.
    - We therefore filter CRPEPToPanchayat by crp_id = <id> directly.

    Same filtering/search/grouping/fields behavior as CRPPanchayatsUnderCrpView.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, id):
        # Normalise & validate ID
        try:
            user_id = int(id)
        except (TypeError, ValueError):
            return Response({'detail': 'Invalid user id'}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch panchayat mappings where crp_id == user_id (master_user_id semantics)
        panchayat_ids = list(
            CRPEPToPanchayat.objects.filter(
                crp_id=user_id
            ).values_list('allocated_panchayat_id', flat=True)
        )

        if not panchayat_ids:
            # Distinguish between "no such CRP user" vs "no mappings"
            if not CRPEP.objects.filter(master_user_id=user_id).exists():
                return Response(
                    {'detail': 'CRP not found for given ID'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            rows = []
        else:
            qs = MasterPanchayat.objects.filter(panchayat_id__in=panchayat_ids).only(
                'panchayat_id',
                'panchayat_name_en',
                'panchayat_name_local',
                'panchayat_code',
                'block_id',
                'district_id',
                'state_id',
            )
            rows = list(
                qs.values(
                    'panchayat_id',
                    'panchayat_name_en',
                    'panchayat_name_local',
                    'panchayat_code',
                    'block_id',
                    'district_id',
                    'state_id',
                )
            )

        # Filters
        filter_map = {
            'block_id': 'block_id',
            'district_id': 'district_id',
            'state_id': 'state_id',
        }
        rows = _apply_list_filters(rows, filter_map, request.GET)

        # Search
        rows = _apply_list_search(
            rows,
            request.GET.get('search'),
            ['panchayat_name_en', 'panchayat_name_local', 'panchayat_code'],
        )

        # Ordering
        rows = _apply_list_ordering(
            rows,
            request.GET.get('ordering'),
            allowed_fields={'panchayat_id', 'panchayat_name_en'},
        )

        # Grouping
        grouped = _apply_list_group_by(rows, request.GET.get('group_by'))
        if grouped is not None:
            grouped = _apply_fields_projection_list(grouped, request.GET.get('fields'))
            return Response(grouped)

        # Fields projection (default subset)
        fields_param = request.GET.get('fields')
        if fields_param:
            rows = _apply_fields_projection_list(rows, fields_param)
        else:
            rows = [
                {
                    'panchayat_id': r['panchayat_id'],
                    'panchayat_name_en': r['panchayat_name_en'],
                    'block_id': r['block_id'],
                    'district_id': r['district_id'],
                    'state_id': r['state_id'],
                }
                for r in rows
            ]

        result = _paginate_plain_list(request, rows)
        return Response(result)


# 4) epsakhi-list/<shg_code>
class EpsakhiListByShgView(APIView):
    """
    GET /api/v1/epsakhi/epsakhi-list/<shg_code>/

    - Lists selected fields of BeneficiaryRecorded whose lokos_shg_code matches the path SHG code.

    Default returned fields:
      lokos_member_code, TH_urid, age, mobile, lokos_shg_code, enterprise_id

    Supports:
      - page, page_size
      - filters: district_id, block_id, panchayat_id, village_id,
                 gender, marital_status, category
      - search: applicant_name, lokos_member_code, mobile, email
      - ordering: age, created_at
      - group_by: district_id, block_id, panchayat_id, village_id,
                  lokos_shg_code, gender, marital_status, category
      - fields: projection
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, shg_code):
        qs = BeneficiaryRecorded.objects.filter(lokos_shg_code=shg_code)

        # Base rows with extended fields used for filters/grouping
        rows = list(
            qs.values(
                'TH_urid',
                'lokos_member_code',
                'age',
                'mobile',
                'lokos_shg_code',
                'enterprise_id',
                'district_id',
                'block_id',
                'panchayat_id',
                'village_id',
                'gender',
                'marital_status',
                'category',
                'applicant_name',
                'email',
                'created_at',
            )
        )

        # Filters
        filter_map = {
            'district_id': 'district_id',
            'block_id': 'block_id',
            'panchayat_id': 'panchayat_id',
            'village_id': 'village_id',
            'gender': 'gender',
            'marital_status': 'marital_status',
            'category': 'category',
        }
        rows = _apply_list_filters(rows, filter_map, request.GET)

        # Search
        rows = _apply_list_search(
            rows,
            request.GET.get('search'),
            ['applicant_name', 'lokos_member_code', 'mobile', 'email'],
        )

        # Ordering
        rows = _apply_list_ordering(
            rows,
            request.GET.get('ordering'),
            allowed_fields={'age', 'created_at'},
        )

        # Grouping
        grouped = _apply_list_group_by(rows, request.GET.get('group_by'))
        if grouped is not None:
            grouped = _apply_fields_projection_list(grouped, request.GET.get('fields'))
            return Response(grouped)

        # Fields projection (default subset)
        fields_param = request.GET.get('fields')
        if fields_param:
            rows = _apply_fields_projection_list(rows, fields_param)
        else:
            rows = [
                {
                    'lokos_member_code': r['lokos_member_code'],
                    'TH_urid': r['TH_urid'],
                    'age': r['age'],
                    'mobile': r['mobile'],
                    'lokos_shg_code': r['lokos_shg_code'],
                    'enterprise_id': r['enterprise_id'],
                }
                for r in rows
            ]

        result = _paginate_plain_list(request, rows)
        return Response(result)


# 5) epsakhi-detail/<member_code>
class EpsakhiDetailByMemberView(APIView):
    """
    GET /api/v1/epsakhi/epsakhi-detail/<member_code>/

    - member_code = BeneficiaryRecorded.lokos_member_code.
    - Returns:
        {
          "beneficiary": <ALL fields of BeneficiaryRecorded>,
          "enterprise_type": "existing" | "new" | null,
          "enterprise": <ALL fields of ExistingEnterprise/NewEnterprise> or null,
          "enterprise_loan_details": [...],
          "enterprise_support_details": [...],
          "enterprise_training_reqs": [...],
          "enterprise_media": [...]
        }

    Supports:
      - fields: comma-separated list of TOP-LEVEL keys to return
                (e.g., fields=beneficiary,enterprise).
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, member_code):
        # take latest recorded beneficiary for this member_code
        br = (
            BeneficiaryRecorded.objects.filter(lokos_member_code=member_code)
            .order_by('-created_at')
            .first()
        )
        if not br:
            return Response({'detail': 'No recorded beneficiary found for given member_code'}, status=status.HTTP_404_NOT_FOUND)

        beneficiary_data = BeneficiaryRecordedSerializer(br).data
        eid = br.enterprise_id

        enterprise_type = None
        enterprise_data = None
        loan_data = []
        support_data = []
        training_data = []
        media_data = []

        if eid:
            existing = ExistingEnterprise.objects.filter(TH_urid=eid).first()
            if existing:
                enterprise_type = 'existing'
                enterprise_data = ExistingEnterpriseSerializer(existing).data
            else:
                new_ent = NewEnterprise.objects.filter(TH_urid=eid).first()
                if new_ent:
                    enterprise_type = 'new'
                    enterprise_data = NewEnterpriseSerializer(new_ent).data

            # related detail tables (keyed by enterprise_id = TH_urid)
            loans = EnterpriseLoanDetail.objects.filter(enterprise_id=eid)
            supports = EnterpriseSupportDetail.objects.filter(enterprise_id=eid)
            trainings = EnterpriseTrainingReq.objects.filter(enterprise_id=eid)
            medias = EnterpriseMedia.objects.filter(enterprise_id=eid)

            loan_data = EnterpriseLoanDetailSerializer(loans, many=True).data
            support_data = EnterpriseSupportDetailSerializer(supports, many=True).data
            training_data = EnterpriseTrainingReqSerializer(trainings, many=True).data
            media_data = EnterpriseMediaSerializer(medias, many=True).data

        response_obj = {
            'beneficiary': beneficiary_data,
            'enterprise_type': enterprise_type,
            'enterprise': enterprise_data,
            'enterprise_loan_details': loan_data,
            'enterprise_support_details': support_data,
            'enterprise_training_reqs': training_data,
            'enterprise_media': media_data,
        }

        fields_param = request.GET.get('fields')
        if fields_param:
            allowed_keys = _parse_csv_param(fields_param)
            response_obj = {k: v for k, v in response_obj.items() if k in allowed_keys}

        return Response(response_obj)
