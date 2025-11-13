"""
core/api/serializers.py

Serializers for core master models.
These serializers are intentionally "full-model" (fields='__all__') for detail endpoints,
and lightweight versions are used for list endpoints when needed by the views.
"""

from rest_framework import serializers
from core import models


# ---------- Roles ----------
class MasterRolesSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterRoles
        fields = '__all__'


# ---------- Users ----------
class MasterUserSerializer(serializers.ModelSerializer):
    role_name = serializers.SerializerMethodField()

    class Meta:
        model = models.MasterUser
        fields = '__all__'  # return all DB fields
        # you can limit fields via ?fields=... in the views if necessary

    def get_role_name(self, obj):
        try:
            return obj.role.name if obj.role else None
        except Exception:
            return None


# ---------- Geography (state/mandal/district/block/panchayat/village) ----------
class MasterStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterState
        fields = '__all__'


class MasterMandalSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterMandal
        fields = '__all__'


class MasterDistrictSerializer(serializers.ModelSerializer):
    state = MasterStateSerializer(read_only=True)
    mandal = MasterMandalSerializer(read_only=True)

    class Meta:
        model = models.MasterDistrict
        fields = '__all__'


class MasterBlockSerializer(serializers.ModelSerializer):
    state = MasterStateSerializer(read_only=True)
    district = MasterDistrictSerializer(read_only=True)

    class Meta:
        model = models.MasterBlock
        fields = '__all__'


class MasterPanchayatSerializer(serializers.ModelSerializer):
    state = MasterStateSerializer(read_only=True)
    district = MasterDistrictSerializer(read_only=True)
    block = MasterBlockSerializer(read_only=True)

    class Meta:
        model = models.MasterPanchayat
        fields = '__all__'


class MasterVillageSerializer(serializers.ModelSerializer):
    state = MasterStateSerializer(read_only=True)
    district = MasterDistrictSerializer(read_only=True)
    block = MasterBlockSerializer(read_only=True)
    panchayat = MasterPanchayatSerializer(read_only=True)

    class Meta:
        model = models.MasterVillage
        fields = '__all__'


# ---------- CLF (list + related) ----------
class MasterClfListSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterClfList
        fields = '__all__'


class MasterClfAddressesSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterClfAddresses
        fields = '__all__'


class MasterClfBanksSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterClfBanks
        fields = '__all__'


class MasterClfPhonesSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterClfPhones
        fields = '__all__'


class MasterClfVoDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterClfVoDetails
        fields = '__all__'


class MasterClfDetailSerializer(serializers.Serializer):
    """
    Combined CLF detail serializer response (not a ModelSerializer) to return masterclf + related arrays.
    """
    clf = MasterClfListSerializer()
    addresses = MasterClfAddressesSerializer(many=True)
    banks = MasterClfBanksSerializer(many=True)
    phones = MasterClfPhonesSerializer(many=True)
    vo_details = MasterClfVoDetailsSerializer(many=True)


# ---------- CLF-related small lists ----------
class MasterMembersUnderClfSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterMembersUnderClf
        fields = '__all__'


class MasterPanchayatsUnderClfSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterPanchayatsUnderClf
        fields = '__all__'


class MasterVillagesUnderClfSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterVillagesUnderClf
        fields = '__all__'


# ---------- SHG (list + detail) ----------
class MasterShgListSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterShgList
        # list usage will often use only a subset, views will call .only(); here we expose all for detail
        fields = '__all__'


class MasterShgAddressesSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterShgAddresses
        fields = '__all__'


class MasterShgBanksSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterShgBanks
        fields = '__all__'


class MasterShgPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterShgPhone
        fields = '__all__'


class MasterShgDetailSerializer(serializers.Serializer):
    shg = MasterShgListSerializer()
    addresses = MasterShgAddressesSerializer(many=True)
    banks = MasterShgBanksSerializer(many=True)
    phones = MasterShgPhoneSerializer(many=True)


# ---------- Beneficiaries ----------
class MasterBeneficiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterBeneficiary
        fields = '__all__'


class MasterBeneficiaryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterBeneficiaryAddress
        fields = '__all__'


class MasterBeneficiaryBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterBeneficiaryBank
        fields = '__all__'


class MasterBeneficiaryDesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterBeneficiaryDesignation
        fields = '__all__'


class MasterBeneficiaryPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterBeneficiaryPhone
        fields = '__all__'


class MasterBeneficiaryDetailSerializer(serializers.Serializer):
    beneficiary = MasterBeneficiarySerializer()
    addresses = MasterBeneficiaryAddressSerializer(many=True)
    banks = MasterBeneficiaryBankSerializer(many=True)
    designations = MasterBeneficiaryDesignationSerializer(many=True)
    phones = MasterBeneficiaryPhoneSerializer(many=True)


# ---------- Geo user scope ----------
class MasterGeoUserScopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MasterGeoUserScope
        fields = '__all__'
