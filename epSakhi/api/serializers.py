# epSakhi/api/serializers.py

from django.db import transaction
from rest_framework import serializers

from epSakhi.models import *

from core.api.serializers import (
    MasterPanchayatListSerializer,
    MasterBlockListSerializer,
    MasterDistrictListSerializer,
)

class CRPEPSerializer(serializers.ModelSerializer):
    # Nested, read-only related objects (FKs on CRPEP)
    district = MasterDistrictListSerializer(read_only=True)
    block = MasterBlockListSerializer(read_only=True)
    panchayat = MasterPanchayatListSerializer(read_only=True)

    class Meta:
        model = CRPEP
        fields = [
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
            'nodal_clf',
            # nested read-only relations
            'district',
            'block',
            'panchayat',
            'created_at',
            'updated_at',
            'deleted_at',
        ]
        read_only_fields = [
            'created_at',
            'updated_at',
            'deleted_at',
            'TH_urid',
            'district',
            'block',
            'panchayat',
        ]

class BeneficiaryRecordedSerializer(serializers.ModelSerializer):
    class Meta:
        model = BeneficiaryRecorded
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'deleted_at', 'TH_urid', 'id']

# ============= EXISTING / NEW ENTERPRISE =============

class ExistingEnterpriseSerializer(serializers.ModelSerializer):
    """
    CRUD for epSakhi_existingEpForm ONLY.
    No nested writes.
    """

    class Meta:
        model = ExistingEnterprise
        fields = '__all__'
        read_only_fields = (
            'id',
            'TH_urid',
            'created_at',
            'updated_at',
            'deleted_at',
        )

class NewEnterpriseSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewEnterprise
        fields = '__all__'
        read_only_fields = ['id', 'TH_urid', 'created_at', 'updated_at', 'deleted_at']

# ============= NEW DETAIL MODELS =============
class EnterpriseLicensesSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseLicenses
        fields = '__all__'
        read_only_fields = ['id', 'TH_urid', 'created_at', 'updated_at', 'deleted_at']

class EnterpriseLoanDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseLoanDetail
        fields = '__all__'
        read_only_fields = ['id', 'TH_urid', 'created_at', 'updated_at', 'deleted_at']

class EnterpriseSubsidyDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseSubsidyDetail
        fields = '__all__'
        read_only_fields = ['id', 'TH_urid', 'created_at', 'updated_at', 'deleted_at']

class EnterpriseShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseShop
        fields = '__all__'
        read_only_fields = ['id', 'TH_urid', 'created_at', 'updated_at', 'deleted_at']

class ShopMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopMedia
        fields = '__all__'
        read_only_fields = ['id', 'TH_urid', 'created_at', 'updated_at', 'deleted_at']

class EnterpriseProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseProduct
        fields = '__all__'
        read_only_fields = ['id', 'TH_urid', 'created_at', 'updated_at', 'deleted_at']

class ProductMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMedia
        fields = '__all__'
        read_only_fields = ['id', 'TH_urid', 'created_at', 'updated_at', 'deleted_at']

class EnterpriseMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseMedia
        fields = '__all__'
        read_only_fields = ['id', 'TH_urid', 'created_at', 'updated_at', 'deleted_at']

class EnterpriseTypeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseTypeCategory
        fields = '__all__'
        read_only_fields = ['id', 'TH_urid', 'created_at', 'updated_at', 'deleted_at']

class EnterpriseSupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseSupport
        fields = '__all__'
        read_only_fields = ['id', 'TH_urid', 'created_at', 'updated_at', 'deleted_at']

class EnterpriseMandatoryFundSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseMandatoryFund
        fields = '__all__'
        read_only_fields = ['id', 'TH_urid', 'created_at', 'updated_at', 'deleted_at']

class EnterpriseTrainingReqSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseTrainingReq
        fields = '__all__'
        read_only_fields = ['id', 'TH_urid', 'created_at', 'updated_at', 'deleted_at']

class TrainingCertificatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingCertificates
        fields = '__all__'
        read_only_fields = ['id', 'TH_urid', 'created_at', 'updated_at', 'deleted_at']

class NoEnterpriseFormSerializer(serializers.ModelSerializer):
    """
    CRUD for epSakhi_noEpForm
    """
    class Meta:
        model = NoEnterpriseForm
        fields = '__all__'

class NoEnterpriseWageSerializer(serializers.ModelSerializer):
    """
    CRUD for epSakhi_noEpWage
    """
    class Meta:
        model = NoEnterpriseWage
        fields = '__all__'
