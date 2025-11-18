# epSakhi/api/serializers.py

from rest_framework import serializers
from epSakhi.models import (
    CRPEP,
    BeneficiaryRecorded,
    ExistingEnterprise,
    NewEnterprise,
    EnterpriseLoanDetail,
    EnterpriseSupportDetail,
    EnterpriseTrainingReq,
    EnterpriseMedia,
)
from core.api.serializers import (
    MasterPanchayatListSerializer,
    MasterBlockListSerializer,
    MasterDistrictListSerializer,
)
from django.db import transaction


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
        read_only_fields = ['created_at', 'updated_at', 'deleted_at', 'TH_urid']


# ============= DETAIL SERIALIZERS =============

class EnterpriseLoanDetailSerializer(serializers.ModelSerializer):
    """
    Used by:
      - /enterprise-loan-details/ 
      - (Optionally) nested in ExistingEnterpriseSerializer for read operations.
    """
    class Meta:
        model = EnterpriseLoanDetail
        fields = '__all__'


class EnterpriseSupportDetailSerializer(serializers.ModelSerializer):
    """
    Used by:
      - /enterprise-support-details/ 
    """
    class Meta:
        model = EnterpriseSupportDetail
        fields = '__all__'


class EnterpriseTrainingReqSerializer(serializers.ModelSerializer):
    """
    Used by:
      - /enterprise-training-reqs/ 
    """
    class Meta:
        model = EnterpriseTrainingReq
        fields = '__all__'


class EnterpriseMediaSerializer(serializers.ModelSerializer):
    """
    Used by:
      - /enterprise-media/ 
    """
    class Meta:
        model = EnterpriseMedia
        fields = '__all__'


# ============= EXISTING / NEW ENTERPRISE =============

class ExistingEnterpriseSerializer(serializers.ModelSerializer):
    """
    NOTE:
    - Frontend will now generally create/update child rows using their own APIs
      (/enterprise-loan-details/, /enterprise-support-details/, etc).
    - The nested write logic below is kept for backward compatibility; if
      `loan_details`, `support_detail`, `training_reqs`, or `media` are not
      sent in the payload, they are simply ignored and no child rows are touched.

    Nested write-only fields (optional):

    - loan_details: [ { institution_name, loan_amount, date_taken, repayment_status }, ... ]
    - support_detail: { department_name, scheme_name, ..., other_support }
    - training_reqs: [ { skill_name, training_type, any_specific_scheme, any_specific_department }, ... ]
    - media: { photo_entrepreneur, photo_enterprise, open_box_photo, close_box_photo, others, certificates }
    """

    loan_details = EnterpriseLoanDetailSerializer(
        many=True, write_only=True, required=False
    )
    support_detail = EnterpriseSupportDetailSerializer(
        write_only=True, required=False
    )
    training_reqs = EnterpriseTrainingReqSerializer(
        many=True, write_only=True, required=False
    )
    media = EnterpriseMediaSerializer(
        write_only=True, required=False
    )

    class Meta:
        model = ExistingEnterprise
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'deleted_at', 'TH_urid']

    @transaction.atomic
    def create(self, validated_data):
        # Pop nested data
        loan_data = validated_data.pop('loan_details', [])
        support_data = validated_data.pop('support_detail', None)
        training_data = validated_data.pop('training_reqs', [])
        media_data = validated_data.pop('media', None)

        # Create main enterprise
        enterprise = super().create(validated_data)
        enterprise_id = enterprise.TH_urid

        # ----- Loan details -----
        if loan_data:
            for ld in loan_data:
                EnterpriseLoanDetail.objects.create(
                    enterprise_id=enterprise_id,
                    **ld
                )
            # keep has_taken_loan in sync
            enterprise.has_taken_loan = True
            enterprise.save(update_fields=['has_taken_loan'])

        # ----- Support detail (single row) -----
        if support_data:
            EnterpriseSupportDetail.objects.create(
                enterprise_id=enterprise_id,
                **support_data
            )

        # ----- Training requirements -----
        if training_data:
            for tr in training_data:
                EnterpriseTrainingReq.objects.create(
                    enterprise_id=enterprise_id,
                    **tr
                )

        # ----- Media (single row) -----
        # NOTE: for real file uploads, prefer /enterprise-media/
        if media_data:
            EnterpriseMedia.objects.create(
                enterprise_id=enterprise_id,
                **media_data
            )

        return enterprise

    @transaction.atomic
    def update(self, instance, validated_data):
        # Pop nested data if present; if not present, we leave related rows untouched.
        loan_data = validated_data.pop('loan_details', None)
        support_data = validated_data.pop('support_detail', None)
        training_data = validated_data.pop('training_reqs', None)
        media_data = validated_data.pop('media', None)

        enterprise = super().update(instance, validated_data)
        enterprise_id = enterprise.TH_urid

        # ----- Loan details -----
        if loan_data is not None:
            EnterpriseLoanDetail.objects.filter(enterprise_id=enterprise_id).delete()
            if loan_data:
                for ld in loan_data:
                    EnterpriseLoanDetail.objects.create(
                        enterprise_id=enterprise_id,
                        **ld
                    )
                enterprise.has_taken_loan = True
            else:
                enterprise.has_taken_loan = False
            enterprise.save(update_fields=['has_taken_loan'])

        # ----- Support detail -----
        if support_data is not None:
            EnterpriseSupportDetail.objects.filter(enterprise_id=enterprise_id).delete()
            if support_data:
                EnterpriseSupportDetail.objects.create(
                    enterprise_id=enterprise_id,
                    **support_data
                )

        # ----- Training requirements -----
        if training_data is not None:
            EnterpriseTrainingReq.objects.filter(enterprise_id=enterprise_id).delete()
            if training_data:
                for tr in training_data:
                    EnterpriseTrainingReq.objects.create(
                        enterprise_id=enterprise_id,
                        **tr
                    )

        # ----- Media -----
        if media_data is not None:
            EnterpriseMedia.objects.filter(enterprise_id=enterprise_id).delete()
            if media_data:
                EnterpriseMedia.objects.create(
                    enterprise_id=enterprise_id,
                    **media_data
                )

        return enterprise


class NewEnterpriseSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewEnterprise
        fields = '__all__'
        read_only_fields = ['TH_urid', 'created_at', 'updated_at', 'deleted_at']