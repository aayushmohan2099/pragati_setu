# epSakhi/api/serializers.py
from rest_framework import serializers
from epSakhi.models import (
    CRPEP, BeneficiaryRecorded, ExistingEnterprise, NewEnterprise,
    EnterpriseLoanDetail, EnterpriseSupportDetail, EnterpriseTrainingReq, EnterpriseMedia
)
from core.api.serializers import MasterPanchayatListSerializer, MasterBlockListSerializer, MasterDistrictListSerializer

class CRPEPSerializer(serializers.ModelSerializer):
    # keep read-only nested light fields (we still can use core lookups endpoints)
    district = MasterDistrictListSerializer(read_only=True)
    block = MasterBlockListSerializer(read_only=True)
    panchayat = MasterPanchayatListSerializer(read_only=True)

    class Meta:
        model = CRPEP
        fields = [
            'id', 'name', 'mobile_number', 'category', 'subcategory', 'marks_obtained', 'TH_urid',
            'district_id', 'block_id', 'panchayat_id', 'lokos_shg_code', 'lokos_member_code', 'nodal_clf',
            'created_at', 'updated_at', 'deleted_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'deleted_at', 'TH_urid']

class BeneficiaryRecordedSerializer(serializers.ModelSerializer):
    class Meta:
        model = BeneficiaryRecorded
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'deleted_at', 'TH_urid']

class ExistingEnterpriseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExistingEnterprise
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'deleted_at', 'TH_urid']

class EnterpriseLoanDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseLoanDetail
        fields = '__all__'

class EnterpriseSupportDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseSupportDetail
        fields = '__all__'

class EnterpriseTrainingReqSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseTrainingReq
        fields = '__all__'

class EnterpriseMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseMedia
        fields = '__all__'

class NewEnterpriseSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewEnterprise
        fields = '__all__'
        read_only_fields = ['TH_urid', 'created_at', 'updated_at', 'deleted_at']
