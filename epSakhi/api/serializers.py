# epSakhi/api/serializers.py
from rest_framework import serializers
from epSakhi.models import CRPEP, BeneficiaryEnterprise
from core.models import MasterDistrict, MasterBlock, MasterPanchayat, MasterShgList, MasterBeneficiary

class MasterDistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterDistrict
        fields = ['district_id','district_name_en','district_short_name_en']

class MasterBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterBlock
        fields = ['block_id','block_name_en','district_id']

class MasterPanchayatSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterPanchayat
        fields = ['panchayat_id','panchayat_name_en','block_id','district_id']

class MasterShgSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterShgList
        fields = ['id','shg_code','name','village_id','panchayat_id','block_id']

class MasterBeneficiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterBeneficiary
        fields = ['member_code','member_name','shg_code','village_id','panchayat_id','block_id']

class CRPEPSerializer(serializers.ModelSerializer):
    district = MasterDistrictSerializer(read_only=True)
    block = MasterBlockSerializer(read_only=True)
    gram_panchayat = MasterPanchayatSerializer(read_only=True)
    shg = MasterShgSerializer(read_only=True)
    nodal_clf = serializers.PrimaryKeyRelatedField(read_only=True)

    district_id = serializers.IntegerField(write_only=True, required=True)
    block_id = serializers.IntegerField(write_only=True, required=True)
    panchayat_id = serializers.IntegerField(write_only=True, required=True)
    shg_code = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    master_user_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = CRPEP
        fields = [
            'id','name','mobile_number','category','subcategory','marks_obtained','TH_urid',
            'district','block','gram_panchayat','shg','nodal_clf',
            'district_id','block_id','panchayat_id','shg_code','master_user_id',
            'created_at','updated_at','deleted_at'
        ]
        read_only_fields = ['created_at','updated_at','deleted_at','TH_urid']

    def create(self, validated_data):
        district_id = validated_data.pop('district_id')
        block_id = validated_data.pop('block_id')
        panchayat_id = validated_data.pop('panchayat_id')
        shg_code = validated_data.pop('shg_code', None)
        master_user_id = validated_data.pop('master_user_id', None)

        instance = CRPEP(
            district_id=district_id,
            block_id=block_id,
            gram_panchayat_id=panchayat_id,
            name=validated_data.get('name'),
            mobile_number=validated_data.get('mobile_number'),
            category=validated_data.get('category'),
            subcategory=validated_data.get('subcategory'),
            marks_obtained=validated_data.get('marks_obtained')
        )
        if shg_code:
            instance.shg_id = shg_code
        if master_user_id:
            instance.master_user_id = master_user_id
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for f in ['name','mobile_number','category','subcategory','marks_obtained']:
            if f in validated_data:
                setattr(instance, f, validated_data[f])
        if 'district_id' in validated_data:
            instance.district_id = validated_data['district_id']
        if 'block_id' in validated_data:
            instance.block_id = validated_data['block_id']
        if 'panchayat_id' in validated_data:
            instance.gram_panchayat_id = validated_data['panchayat_id']
        if 'shg_code' in validated_data:
            instance.shg_id = validated_data['shg_code']
        if 'master_user_id' in validated_data:
            instance.master_user_id = validated_data['master_user_id']
        instance.save()
        return instance

class BeneficiaryEnterpriseSerializer(serializers.ModelSerializer):
    beneficiary = MasterBeneficiarySerializer(read_only=True)
    beneficiary_member_code = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = BeneficiaryEnterprise
        fields = '__all__'
        read_only_fields = ['created_at','updated_at','deleted_at']

    def create(self, validated_data):
        member_code = validated_data.pop('beneficiary_member_code')
        validated_data['beneficiary_id'] = member_code
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'beneficiary_member_code' in validated_data:
            instance.beneficiary_id = validated_data.pop('beneficiary_member_code')
        return super().update(instance, validated_data)
