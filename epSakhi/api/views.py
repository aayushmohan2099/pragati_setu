# epSakhi/api/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from epSakhi.models import CRPEP, BeneficiaryEnterprise
from core.models import MasterUser
from .serializers import CRPEPSerializer, BeneficiaryEnterpriseSerializer
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.http import StreamingHttpResponse
import csv
from io import StringIO
from django.db.models import Prefetch

CACHE_TTL = 30

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
        # If fields include related names, leave them out (we only support model columns here)
        # Return a ValuesQuerySet for speed
        return qs.values(*cols)


class CRPEPViewSet(viewsets.ModelViewSet, BaseProjectionMixin):
    queryset = CRPEP.objects.all()
    serializer_class = CRPEPSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name','mobile_number']
    ordering_fields = ['id','created_at']

    def get_queryset(self):
        # Base queryset optimized: restrict columns and eager-load relations for detail usage
        qs = CRPEP.objects.select_related('district', 'block', 'gram_panchayat', 'master_user', 'shg', 'nodal_clf').all().order_by('-id').only(
            'id','name','mobile_number','category','subcategory','marks_obtained','TH_urid',
            'district_id','block_id','panchayat_id','shg_id','master_user_id','nodal_clf_id',
            'created_at','updated_at','deleted_at'
        )

        user = self.request.user
        try:
            mu = MasterUser.objects.get(username=user.username)
            # existing behaviour: if role is 'crp_ep' restrict to user
            if getattr(mu, 'role', None) and getattr(mu.role, 'id', None) and mu.get_role_name() == 'crp_ep':
                qs = qs.filter(master_user_id=mu.id)
        except Exception:
            # don't break on errors; return base qs
            pass

        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        # projection if requested
        projected = self.apply_fields_projection(request, qs)
        if isinstance(projected, (list,)) or hasattr(projected, 'model') and projected.query.is_values:
            # values() queryset
            page = self.paginate_queryset(projected)
            if page is not None:
                return self.get_paginated_response(list(page))
            return Response(list(projected))
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(CACHE_TTL))
    def mylist(self, request):
        qs = self.get_queryset()
        # user-specific list already handled by get_queryset
        projected = self.apply_fields_projection(request, qs)
        if hasattr(projected, 'query') and projected.query.is_values:
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
        qs = self.get_queryset()
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['id','name','district_id','block_id','panchayat_id','shg_code','mobile_number','category','marks_obtained'])
        # Use iterator to reduce memory (if dataset big)
        for r in qs.iterator():
            writer.writerow([r.id, r.name, r.district_id, r.block_id, r.gram_panchayat_id, getattr(r, 'shg_id', ''), r.mobile_number, r.category, r.marks_obtained])
        buffer.seek(0)
        response = StreamingHttpResponse(buffer, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="crpep_export.csv"'
        return response


class CRPPanchayatMappingViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def link(self, request, pk=None):
        crp_id = pk
        panchayat_ids = request.data.get('panchayat_ids', [])
        if not isinstance(panchayat_ids, list):
            return Response({'detail':'panchayat_ids must be list'}, status=status.HTTP_400_BAD_REQUEST)
        from epSakhi.models import CRPEPToPanchayat
        created = []
        with transaction.atomic():
            for pid in panchayat_ids:
                obj, _ = CRPEPToPanchayat.objects.get_or_create(crp_id=crp_id, allocated_panchayat_id=pid)
                created.append(obj.id)
        return Response({'created_ids': created})


class BeneficiaryEnterpriseViewSet(viewsets.ModelViewSet, BaseProjectionMixin):
    queryset = BeneficiaryEnterprise.objects.all().order_by('-id')
    serializer_class = BeneficiaryEnterpriseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['enterprise_name','main_product_service']
    ordering_fields = ['id','created_at']

    def get_queryset(self):
        # Optimize: select_related recorded_by_user and beneficiary basic FK for list (lightweight)
        qs = BeneficiaryEnterprise.objects.select_related('recorded_by_user', 'beneficiary').all().order_by('-id').only(
            'id', 'beneficiary_id', 'recorded_by_user_id', 'enterprise_name', 'enterprise_type', 'created_at', 'updated_at'
        )
        user = self.request.user
        try:
            mu = MasterUser.objects.get(username=user.username)
            if getattr(mu, 'role', None) and mu.get_role_name() == 'crp_ep':
                qs = qs.filter(recorded_by_user_id=mu.id)
        except Exception:
            pass
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        projected = self.apply_fields_projection(request, qs)
        if hasattr(projected, 'query') and projected.query.is_values:
            page = self.paginate_queryset(projected)
            return self.get_paginated_response(list(page) if page is not None else list(projected))
        return super().list(request, *args, **kwargs)
