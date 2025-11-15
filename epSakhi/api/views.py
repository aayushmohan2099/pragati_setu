# epSakhi/api/views.py
import requests
import json
from django.conf import settings
from django.core.cache import cache
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from epSakhi.models import (
    CRPEP, BeneficiaryRecorded, ExistingEnterprise, NewEnterprise,
    EnterpriseLoanDetail, EnterpriseSupportDetail, EnterpriseTrainingReq, EnterpriseMedia
)
from .serializers import (
    CRPEPSerializer, BeneficiaryRecordedSerializer, ExistingEnterpriseSerializer, NewEnterpriseSerializer,
    EnterpriseLoanDetailSerializer, EnterpriseSupportDetailSerializer, EnterpriseTrainingReqSerializer, EnterpriseMediaSerializer
)
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

# cache ttl in seconds
SHG_CACHE_TTL = getattr(settings, 'SHG_CACHE_TTL', 60*5)  # default 5 minutes

# Helper to call APISETU
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

# ---- SHG list proxy (cache + filtering + projection + grouping) ----
from rest_framework.views import APIView

class UpsrlmShgListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, block_id):
        # Step 1: fetch or read cached JSON for block_id
        cache_key = f"upsrlm_shg_list:{block_id}"
        j = cache.get(cache_key)
        if j is None:
            try:
                j = _call_apisetu_shg_list(block_id)
            except Exception as e:
                return Response({'detail': f'Error fetching remote shg-list: {str(e)}'}, status=502)
            cache.set(cache_key, j, SHG_CACHE_TTL)

        # j is expected to be a list of SHG dicts
        queryset = j  

        # Convert to Query-like pipeline: filtering, search, ordering, grouping, pagination, fields projection

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
            val = p_special in ('1','true','True')
            queryset = [x for x in queryset if bool(int(x.get('specialShg', 0))) == val]
        if p_social:
            queryset = [x for x in queryset if x.get('socialCategory') == p_social]

        # Search: name, nic_code, shg_code
        q = request.GET.get('search')
        if q:
            ql = q.lower()
            def matches(item):
                return ql in (str(item.get('name','')).lower() or '') or ql in (str(item.get('nicCode','')).lower() or '') or ql in (str(item.get('code','')).lower() or '')
            queryset = [x for x in queryset if matches(x)]

        # Ordering: formation_date (-asc,-dsc)
        ordering = request.GET.get('ordering')
        if ordering:
            reverse = ordering.startswith('-')
            key = ordering.lstrip('-')
            def key_fn(it):
                return it.get('formationDate') or ''
            queryset = sorted(queryset, key=key_fn, reverse=reverse)

        # group_by (aggregation): district_id, block_id, panchayat_id, village_id, shgType, social_category
        group_by = request.GET.get('group_by')
        if group_by:
            keys = [k.strip() for k in group_by.split(',') if k.strip()]
            # simple aggregation counts
            agg = {}
            for it in queryset:
                group_key = tuple(str(it.get(k)) for k in keys)
                agg[group_key] = agg.get(group_key, 0) + 1
            # return list of dicts {group:..., count:...}
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

        # pagination: page (1-based), page_size (default 10, max 100)
        try:
            page = int(request.GET.get('page', '1'))
            page_size = min(100, int(request.GET.get('page_size', '10')))
        except Exception:
            page, page_size = 1, 10
        total = len(queryset)
        start = (page - 1) * page_size
        end = start + page_size
        data = queryset[start:end]
        return Response({
            'meta': {'page': page, 'page_size': page_size, 'total': total},
            'data': data
        })


# ---- SHG members proxy ----
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
        # apply filters: aadhar_verified, gender, religion, social_category, designation
        if 'aadhar_verified' in request.GET:
            av = request.GET.get('aadhar_verified') in ('1','true','True')
            members = [m for m in members if bool(m.get('aadhar_verified')) == av]
        for f in ('gender','religion','social_category'):
            if request.GET.get(f):
                members = [m for m in members if m.get(f) == request.GET.get(f)]
        # designation filter requires searching nested member_designations for designation
        if request.GET.get('designation'):
            des = request.GET.get('designation')
            members = [m for m in members if any(d.get('designation') == des for d in m.get('member_designations', []))]

        # search fields: member_name, member_code, nic_member_code, member_guid, phone_no
        q = request.GET.get('search')
        if q:
            ql = q.lower()
            def mmatch(m):
                if ql in (m.get('member_name') or '').lower(): return True
                if ql in (str(m.get('member_code')) or '').lower(): return True
                if ql in (m.get('nic_member_code') or '').lower(): return True
                if ql in (m.get('member_guid') or '').lower(): return True
                # phone no nested
                for ph in m.get('member_phones', []):
                    if ql in str(ph.get('phone_no') or ''):
                        return True
                return False
            members = [m for m in members if mmatch(m)]

        # ordering: creation_date, joining_date, dob
        ordering = request.GET.get('ordering')
        if ordering:
            reverse = ordering.startswith('-')
            key = ordering.lstrip('-')
            members = sorted(members, key=lambda m: m.get(key) or '', reverse=reverse)

        # grouping similar to list
        group_by = request.GET.get('group_by')
        if group_by:
            keys = [k.strip() for k in group_by.split(',') if k.strip()]
            agg = {}
            for it in members:
                group_key = tuple(str(it.get(k)) for k in keys)
                agg[group_key] = agg.get(group_key, 0) + 1
            out = [{'group': dict(zip(keys, k)), 'count': v} for k, v in agg.items()]
            return Response(out)

        # fields projection - only a subset supported
        fields = request.GET.get('fields')
        if fields:
            cols = [c.strip() for c in fields.split(',') if c.strip()]
            members = [{c: m.get(c) for c in cols} for m in members]

        # pagination
        try:
            page = int(request.GET.get('page', '1'))
            page_size = min(100, int(request.GET.get('page_size', '10')))
        except Exception:
            page, page_size = 1, 10
        total = len(members)
        start = (page - 1) * page_size
        end = start + page_size
        return Response({'meta': {'page': page, 'page_size': page_size, 'total': total}, 'data': members[start:end]})


# ---- SHG detail excluding members (for other metadata queries) ----
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


# ---- BeneficiaryRecorded viewset ----
from rest_framework import mixins
class BeneficiaryRecordedViewSet(viewsets.ModelViewSet, BaseProjectionMixin):
    queryset = BeneficiaryRecorded.objects.all().order_by('-created_at')
    serializer_class = BeneficiaryRecordedSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['applicant_name', 'lokos_member_code', 'mobile', 'email', 'enterprise_id']
    ordering_fields = ['age', 'created_at']

    def get_queryset(self):
        qs = BeneficiaryRecorded.objects.all().order_by('-created_at')
        # apply simple filters from query params: district_id, block_id, panchayat_id, village_id, lokos_shg_code, gender, marital_status, category
        params = self.request.GET
        if params.get('district_id'): qs = qs.filter(district_id=int(params.get('district_id')))
        if params.get('block_id'): qs = qs.filter(block_id=int(params.get('block_id')))
        if params.get('panchayat_id'): qs = qs.filter(panchayat_id=int(params.get('panchayat_id')))
        if params.get('village_id'): qs = qs.filter(village_id=int(params.get('village_id')))
        if params.get('lokos_shg_code'): qs = qs.filter(lokos_shg_code=params.get('lokos_shg_code'))
        if params.get('gender'): qs = qs.filter(gender=params.get('gender'))
        if params.get('marital_status'): qs = qs.filter(marital_status=params.get('marital_status'))
        if params.get('category'): qs = qs.filter(category=params.get('category'))
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        # grouping
        group_by = request.GET.get('group_by')
        if group_by:
            keys = [k.strip() for k in group_by.split(',') if k.strip()]
            # perform aggregation counts via values in queryset
            vals = qs.values(*keys).order_by().annotate(count=models.Count('TH_urid'))
            return Response(list(vals))
        # fields projection
        fields = request.GET.get('fields')
        if fields:
            cols = [c.strip() for c in fields.split(',') if c.strip()]
            qs = qs.values(*cols)
            page = self.paginate_queryset(qs)
            return self.get_paginated_response(list(page) if page is not None else list(qs))
        return super().list(request, *args, **kwargs)


# ---- Enterprise viewsets ----
class ExistingEnterpriseViewSet(viewsets.ModelViewSet):
    queryset = ExistingEnterprise.objects.all().order_by('-created_at')
    serializer_class = ExistingEnterpriseSerializer
    permission_classes = [IsAuthenticated]

class NewEnterpriseViewSet(viewsets.ModelViewSet):
    queryset = NewEnterprise.objects.all().order_by('-created_at')
    serializer_class = NewEnterpriseSerializer
    permission_classes = [IsAuthenticated]
