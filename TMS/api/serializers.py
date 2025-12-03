# TMS/api/serializers.py

from rest_framework import serializers
from TMS import models as tms_models


class SoftDeleteModelSerializer(serializers.ModelSerializer):
    """
    Base serializer for all models using SoftDeleteMixin.
    Common audit fields are read-only.
    """

    class Meta:
        abstract = True
        read_only_fields = (
            "id",
            "TH_urid",
            "created_at",
            "updated_at",
            "deleted_at",
            "created_by",
            "updated_by",
            "deleted_by",
            "is_active",
        )


# ----------------------------
# TrainingTheme + TrainingPlan
# ----------------------------

class TrainingThemeSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingTheme
        fields = "__all__"


class TrainingPlanSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPlan
        fields = "__all__"


class TrainingPlanDetailSerializer(SoftDeleteModelSerializer):
    theme = TrainingThemeSerializer(read_only=True)
    requests = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=True,
    )

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPlan
        fields = "__all__"
        depth = 1


class TrainingThemeDetailSerializer(SoftDeleteModelSerializer):
    training_plans = TrainingPlanSerializer(
        many=True,
        read_only=True,
        source="THEME",  # related_name on TrainingPlan.theme
    )

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingTheme
        fields = "__all__"
        depth = 1


# ----------------------------
# MasterTrainer & Certificates
# ----------------------------

class MasterTrainerSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.MasterTrainer
        fields = "__all__"


class MasterTrainerCertificateSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.MasterTrainerCertificate
        fields = "__all__"


class MasterTrainerDetailSerializer(SoftDeleteModelSerializer):
    certificates = MasterTrainerCertificateSerializer(many=True, read_only=True)

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.MasterTrainer
        fields = "__all__"
        depth = 1


# ----------------------------
# Training Partner + related
# ----------------------------

class TrainingPartnerSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPartner
        fields = "__all__"


class TrainingPartnerBankSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPartnerBank
        fields = "__all__"


class TrainingPartnerCPSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPartnerCP
        fields = "__all__"


class TrainingPartnerCentreSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPartnerCentre
        fields = "__all__"


class TrainingPartnerCentreRoomsSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPartnerCentreRooms
        fields = "__all__"


class TPCPToCentreSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TPCPToCentre
        fields = "__all__"


class TrainingPartnerSubmissionSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPartnerSubmission
        fields = "__all__"


class TrainingPartnerCentreDetailSerializer(SoftDeleteModelSerializer):
    """
    DETAIL serializer for centre including nested rooms.
    """
    rooms = TrainingPartnerCentreRoomsSerializer(many=True, read_only=True)

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPartnerCentre
        fields = "__all__"
        depth = 1


class TrainingPartnerDetailSerializer(SoftDeleteModelSerializer):
    banks = TrainingPartnerBankSerializer(many=True, read_only=True)
    contact_person = TrainingPartnerCPSerializer(many=True, read_only=True)
    centres = TrainingPartnerCentreSerializer(many=True, read_only=True)
    submissions = TrainingPartnerSubmissionSerializer(many=True, read_only=True)
    targets = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPartner
        fields = "__all__"
        depth = 1


# ----------------------------
# TrainingPartnerTargets
# ----------------------------

class TrainingPartnerTargetsSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPartnerTargets
        fields = "__all__"


# ----------------------------
# TRPUserScope
# ----------------------------

class TRPUserScopeSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TRPUserScope
        fields = "__all__"


# ----------------------------
# TrainingRequest + TRBeneficiary + TRTrainer
# ----------------------------

class TrainingRequestSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingRequest
        fields = "__all__"


class TRBeneficiarySerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TRBeneficiary
        fields = "__all__"


class TRBeneficiaryDetailSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TRBeneficiary
        fields = "__all__"
        depth = 1


class TRTrainerSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TRTrainer
        fields = "__all__"


class TRTrainerDetailSerializer(SoftDeleteModelSerializer):
    """
    DETAIL serializer for TRTrainer – includes nested trainer + training.
    """
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TRTrainer
        fields = "__all__"
        depth = 1


class TrainingRequestDetailSerializer(SoftDeleteModelSerializer):
    beneficiary_registrations = TRBeneficiarySerializer(many=True, read_only=True)
    trainer_registrations = TRTrainerSerializer(many=True, read_only=True)
    batches = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingRequest
        fields = "__all__"
        depth = 1


# ----------------------------
# Batch + participants/trainers
# ----------------------------

class BatchSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.Batch
        fields = "__all__"


class BatchMasterTrainerSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchMasterTrainer
        fields = "__all__"


class BatchBeneficiarySerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchBeneficiary
        fields = "__all__"


class BatchTrainerSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchTrainer
        fields = "__all__"


class BatchEkycVerificationSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchEkycVerification
        fields = "__all__"


class BatchAttendanceSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchAttendance
        fields = "__all__"


class ParticipantAttendanceSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.ParticipantAttendance
        fields = "__all__"


class BatchAttendanceDetailSerializer(SoftDeleteModelSerializer):
    participant_records = ParticipantAttendanceSerializer(many=True, read_only=True)

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchAttendance
        fields = "__all__"
        depth = 1


class BatchDetailSerializer(SoftDeleteModelSerializer):
    master_trainer_participations = BatchMasterTrainerSerializer(many=True, read_only=True)
    trainer_participations = BatchTrainerSerializer(many=True, read_only=True)
    beneficiary_participations = BatchBeneficiarySerializer(many=True, read_only=True)
    ekyc_verifications = BatchEkycVerificationSerializer(many=True, read_only=True)
    attendances = BatchAttendanceDetailSerializer(many=True, read_only=True)

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.Batch
        fields = "__all__"
        depth = 1


# ----------------------------
# Batch Closure & Certificates
# ----------------------------

class TPBatchCostBreakupSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TPBatchCostBreakup
        fields = "__all__"


class BatchCostSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchCost
        fields = "__all__"


class BatchMediaSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchMedia
        fields = "__all__"


class BatchClosureRequestSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchClosureRequest
        fields = "__all__"


class BatchClosureRequestDetailSerializer(SoftDeleteModelSerializer):
    batch_costing = BatchCostSerializer(read_only=True)
    batch_pictures = BatchMediaSerializer(read_only=True)

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchClosureRequest
        fields = "__all__"
        depth = 1


class TRClosureSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TRClosure
        fields = "__all__"


class BatchParticipantCertificateSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchParticipantCertificate
        fields = "__all__"


class BatchParticipantCertificateDetailSerializer(SoftDeleteModelSerializer):
    batch = BatchSerializer(read_only=True)

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchParticipantCertificate
        fields = "__all__"
        depth = 1
