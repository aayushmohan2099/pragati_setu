# epSakhi/api/serializers.py
from rest_framework import serializers
from epSakhi.models import CRPEP, BeneficiaryEnterprise
from core.models import (
    MasterDistrict, MasterBlock, MasterPanchayat,
    MasterShgList, MasterBeneficiary
)


# ---------- Basic master serializers (used by core lookups) ----------
class MasterDistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterDistrict
        fields = ['district_id', 'district_name_en', 'state_id']


class MasterBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterBlock
        fields = ['block_id', 'block_name_en', 'district_id', 'is_aspirational']


class MasterPanchayatSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterPanchayat
        fields = ['panchayat_id', 'panchayat_name_en', 'block_id']


# ---------- SHG list serializer (lightweight) ----------
class MasterShgListSerializer(serializers.ModelSerializer):
    block_id = serializers.IntegerField(source='block_id', read_only=True)
    district_id = serializers.IntegerField(source='district_id', read_only=True)
    village_id = serializers.IntegerField(source='village_id', read_only=True)

    class Meta:
        model = MasterShgList
        fields = ['id', 'shg_code', 'name', 'block_id', 'district_id', 'village_id', 'is_active']


# ---------- SHG detail serializer (base shg fields only) ----------
class MasterShgDetailSerializer(serializers.ModelSerializer):
    block_id = serializers.IntegerField(source='block_id', read_only=True)
    district_id = serializers.IntegerField(source='district_id', read_only=True)
    panchayat_id = serializers.IntegerField(source='panchayat_id', read_only=True)
    village_id = serializers.IntegerField(source='village_id', read_only=True)

    class Meta:
        model = MasterShgList
        fields = [
            'id', 'shg_code', 'name', 'formation_date', 'latitude', 'longitude',
            'is_active', 'block_id', 'district_id', 'panchayat_id', 'village_id'
        ]


# ---------- Beneficiary list serializer (lightweight) ----------
class MasterBeneficiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterBeneficiary
        fields = ['member_code', 'member_name', 'dob', 'gender', 'shg_code']


# ---------- Beneficiary detail serializer (base) ----------
class MasterBeneficiaryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterBeneficiary
        fields = [
            'member_code', 'member_name', 'dob', 'gender', 'joining_date',
            'shg_code', 'state_id', 'district_id', 'block_id'
        ]


# ---------- CRP / EP serializers ----------
class CRPEPSerializer(serializers.ModelSerializer):
    # read-only nested representations
    district = MasterDistrictSerializer(read_only=True)
    block = MasterBlockSerializer(read_only=True)
    gram_panchayat = MasterPanchayatSerializer(read_only=True)
    # show lightweight SHG info
    shg = MasterShgListSerializer(read_only=True)
    nodal_clf = serializers.PrimaryKeyRelatedField(read_only=True)

    # write-only ids (for create/update)
    district_id = serializers.IntegerField(write_only=True, required=True)
    block_id = serializers.IntegerField(write_only=True, required=True)
    panchayat_id = serializers.IntegerField(write_only=True, required=True)
    shg_code = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    master_user_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = CRPEP
        fields = [
            'id', 'name', 'mobile_number', 'category', 'subcategory', 'marks_obtained', 'TH_urid',
            'district', 'block', 'gram_panchayat', 'shg', 'nodal_clf',
            'district_id', 'block_id', 'panchayat_id', 'shg_code', 'master_user_id',
            'created_at', 'updated_at', 'deleted_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'deleted_at', 'TH_urid']

    def create(self, validated_data):
        district_id = validated_data.pop('district_id')
        block_id = validated_data.pop('block_id')
        panchayat_id = validated_data.pop('panchayat_id')
        shg_code = validated_data.pop('shg_code', None)
        master_user_id = validated_data.pop('master_user_id', None)

        # Build create kwargs for known model fields
        create_kwargs = {
            'district_id': district_id,
            'block_id': block_id,
            'gram_panchayat_id': panchayat_id,
            'name': validated_data.get('name'),
            'mobile_number': validated_data.get('mobile_number'),
            'category': validated_data.get('category'),
            'subcategory': validated_data.get('subcategory'),
            'marks_obtained': validated_data.get('marks_obtained'),
        }

        # allow optional fields if provided
        if shg_code:
            # try to set FK id attribute safely
            create_kwargs['shg_id'] = shg_code
        if master_user_id:
            create_kwargs['master_user_id'] = master_user_id

        instance = CRPEP.objects.create(**create_kwargs)
        return instance

    def update(self, instance, validated_data):
        # update simple fields
        for f in ['name', 'mobile_number', 'category', 'subcategory', 'marks_obtained']:
            if f in validated_data:
                setattr(instance, f, validated_data[f])

        # update related id fields if provided
        if 'district_id' in validated_data:
            setattr(instance, 'district_id', validated_data['district_id'])
        if 'block_id' in validated_data:
            setattr(instance, 'block_id', validated_data['block_id'])
        if 'panchayat_id' in validated_data:
            setattr(instance, 'gram_panchayat_id', validated_data['panchayat_id'])
        if 'shg_code' in validated_data:
            # use attribute name that matches model (shg_id)
            setattr(instance, 'shg_id', validated_data['shg_code'])
        if 'master_user_id' in validated_data:
            setattr(instance, 'master_user_id', validated_data['master_user_id'])

        instance.save()
        return instance


class BeneficiaryEnterpriseSerializer(serializers.ModelSerializer):
    beneficiary = MasterBeneficiarySerializer(read_only=True)
    beneficiary_member_code = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = BeneficiaryEnterprise
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'deleted_at']

    def create(self, validated_data):
        member_code = validated_data.pop('beneficiary_member_code')
        # map incoming member_code to model's FK field name - commonly 'beneficiary_id'
        validated_data['beneficiary_id'] = member_code
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'beneficiary_member_code' in validated_data:
            instance.beneficiary_id = validated_data.pop('beneficiary_member_code')
        return super().update(instance, validated_data)
