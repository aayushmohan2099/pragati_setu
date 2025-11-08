# core/api/lookups.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from core.models import MasterDistrict, MasterBlock, MasterPanchayat, MasterVillage, MasterShgList, MasterBeneficiary
from epSakhi.api.serializers import MasterDistrictSerializer, MasterBlockSerializer, MasterPanchayatSerializer, MasterShgSerializer, MasterBeneficiarySerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

CACHE_TTL = 300

class DistrictListView(APIView):
    permission_classes = (permissions.AllowAny,)

    @method_decorator(cache_page(CACHE_TTL))
    def get(self, request):
        qs = MasterDistrict.objects.all().order_by('district_name_en')
        serializer = MasterDistrictSerializer(qs, many=True)
        return Response(serializer.data)

class BlockListView(APIView):
    permission_classes = (permissions.AllowAny,)

    @method_decorator(cache_page(CACHE_TTL))
    def get(self, request, district_id=None):
        qs = MasterBlock.objects.filter(district_id=district_id).order_by('block_name_en')
        serializer = MasterBlockSerializer(qs, many=True)
        return Response(serializer.data)

class PanchayatListView(APIView):
    permission_classes = (permissions.AllowAny,)

    @method_decorator(cache_page(CACHE_TTL))
    def get(self, request, block_id=None):
        qs = MasterPanchayat.objects.filter(block_id=block_id).order_by('panchayat_name_en')
        serializer = MasterPanchayatSerializer(qs, many=True)
        return Response(serializer.data)

class VillageListView(APIView):
    permission_classes = (permissions.AllowAny,)

    @method_decorator(cache_page(CACHE_TTL))
    def get(self, request, panchayat_id=None):
        qs = MasterVillage.objects.filter(panchayat_id=panchayat_id, is_active=True).order_by('village_name_english')
        data = [{'village_id': v.village_id, 'village_name': v.village_name_english, 'beneficiary_count': 0} for v in qs]
        return Response(data)

class ShgListView(APIView):
    permission_classes = (permissions.AllowAny,)

    @method_decorator(cache_page(CACHE_TTL))
    def get(self, request, village_id=None):
        qs = MasterShgList.objects.filter(village_id=village_id).order_by('name')
        serializer = MasterShgSerializer(qs, many=True)
        return Response(serializer.data)

class BeneficiaryListView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, shg_code=None):
        qs = MasterBeneficiary.objects.filter(shg_code=shg_code).order_by('member_name')
        serializer = MasterBeneficiarySerializer(qs, many=True)
        return Response(serializer.data)
