# TMS/api/serializers.py

from rest_framework import serializers
from django.apps import apps
from datetime import datetime
from TMS import models as tms_models
from core import models as core_models


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
        
class TPCPToCentreDetailSerializer(SoftDeleteModelSerializer):
    """
    DETAIL serializer for centre including nested rooms.
    """
    allocated_centre = TrainingPartnerCentreSerializer(read_only=True)
    contact_person = TrainingPartnerCPSerializer(read_only=True)

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TPCPToCentre
        fields = "__all__"
        depth = 1

class TrainingPartnerSubmissionSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPartnerSubmission
        fields = "__all__"


class TrainingPartnerCentreDetailSerializer(SoftDeleteModelSerializer):
    """
    DETAIL serializer for centre including nested rooms.
    """
    rooms = TrainingPartnerCentreRoomsSerializer(many=True, read_only=True)
    submissions = TrainingPartnerSubmissionSerializer(many=True, read_only=True)

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

class BatchScheduleSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchSchedule
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

class BatchCostDetailSerializer(SoftDeleteModelSerializer):
    batch_expenses = TPBatchCostBreakupSerializer(read_only=True)
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchCost
        fields = "__all__"
        depth = 1

class BatchMediaSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchMedia
        fields = "__all__"


class BatchClosureRequestSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchClosureRequest
        fields = "__all__"


class BatchClosureRequestDetailSerializer(SoftDeleteModelSerializer):
    batch = BatchSerializer(read_only=True)
    batch_costing = BatchCostSerializer(read_only=True)

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

# ----------------------------
# Reports
# ----------------------------

class MasterDistrictReportSerializer(SoftDeleteModelSerializer):
    district_id = serializers.IntegerField(source='districtid')
    district_name_en = serializers.CharField(source='districtnameen')
    district_short_name_en = serializers.CharField(source='districtshortnameen')

    class Meta(SoftDeleteModelSerializer.Meta):
        model = core_models.MasterDistrict
        fields = ['district_id', 'district_name_en', 'district_short_name_en']

class MasterBlockReportSerializer(SoftDeleteModelSerializer):
    block_id = serializers.IntegerField(source='blockid')
    block_name_en = serializers.CharField(source='blocknameen')
    block_name_local = serializers.CharField(source='blocknamelocal')
    is_aspirational = serializers.IntegerField(source='isaspirational')

    class Meta(SoftDeleteModelSerializer.Meta):
        model = core_models.MasterBlock
        fields = ['block_id', 'block_name_en', 'block_name_local', 'is_aspirational']

class MasterPanchayatReportSerializer(SoftDeleteModelSerializer):
    panchayat_id = serializers.IntegerField(source='panchayatid')
    panchayat_name_en = serializers.CharField(source='panchayatnameen')
    panchayat_name_local = serializers.CharField(source='panchayatnamelocal')

    class Meta(SoftDeleteModelSerializer.Meta):
        model = core_models.MasterPanchayat
        fields = ['panchayat_id', 'panchayat_name_en', 'panchayat_name_local']

class MasterVillageReportSerializer(SoftDeleteModelSerializer):
    village_id = serializers.IntegerField(source='villageid')
    village_name_english = serializers.CharField(source='villagenameenglish')
    village_name_local = serializers.CharField(source='villagenamelocal')

    class Meta(SoftDeleteModelSerializer.Meta):
        model = core_models.MasterVillage
        fields = ['village_id', 'village_name_english', 'village_name_local']

# ----------------------------
# TrainingTheme & TrainingPlan (EXACT fields)
# ----------------------------

class TrainingThemeReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    theme_name = serializers.CharField(source='themename')

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingTheme
        fields = ['id', 'theme_name']

class TrainingPlanReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    training_name = serializers.CharField(source='trainingname')
    theme = TrainingThemeReportSerializer(read_only=True)

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPlan
        fields = ['id', 'training_name', 'theme', 'typeoftraining', 'leveloftraining', 'noofdays', 'approvalstatus']

# ----------------------------
# TrainingPartner (EXACT fields)
# ----------------------------

class TrainingPartnerReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPartner
        fields = ['id', 'name', 'email', 'address', 'tpmregistrationno', 'mouform']

# ----------------------------
# TrainingPartnerCentre + Nested (EXACT model fields)
# ----------------------------

class TrainingPartnerCentreReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    serial_number = serializers.IntegerField(source='serialnumber')
    district = MasterDistrictReportSerializer(read_only=True)
    block = MasterBlockReportSerializer(read_only=True)
    panchayat = MasterPanchayatReportSerializer(read_only=True)
    village = MasterVillageReportSerializer(read_only=True)

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPartnerCentre
        fields = [
            'id', 'serial_number', 'district', 'block', 'panchayat', 'village',
            'venuename', 'venueaddress', 'traininghallcount', 'traininghallcapacity',
            'securityarrangements', 'toiletsbathrooms', 'powerwaterfacility',
            'medicalkit', 'centretype', 'openspace', 'fieldvisitfacility',
            'transportfacility', 'diningfacility', 'otherdetails'
        ]

class TrainingPartnerCentreRoomsReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    room_capacity = serializers.IntegerField(source='roomcapacity')

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPartnerCentreRooms
        fields = ['id', 'roomname', 'room_capacity']

class TrainingPartnerSubmissionReportSerializer(SoftDeleteModelSerializer):
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingPartnerSubmission
        fields = ['category', 'file', 'notes']

# ----------------------------
# MasterTrainer (EXACT fields)
# ----------------------------

class MasterTrainerReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    empanel_district = MasterDistrictReportSerializer(read_only=True, source='empaneldistrict')
    empanel_block = MasterBlockReportSerializer(read_only=True, source='empanelblock')

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.MasterTrainer
        fields = [
            'id', 'fullname', 'dateofbirth', 'mobileno', 'aadharno',
            'empanel_district', 'empanel_block', 'socialcategory', 'gender',
            'education', 'maritalstatus', 'parentorspousename', 'skills',
            'successrate', 'designation'
        ]

# ----------------------------
# TRBeneficiary (EXACT fields from model)
# ----------------------------

class TRBeneficiaryReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    lokos_shg_code = serializers.CharField(source='lokosshgcode')
    lokos_member_code = serializers.CharField(source='lokosmembercode')
    member_name = serializers.CharField(source='membername')
    district = MasterDistrictReportSerializer(read_only=True)
    block = MasterBlockReportSerializer(read_only=True)
    panchayat = MasterPanchayatReportSerializer(read_only=True)
    village = MasterVillageReportSerializer(read_only=True)

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TRBeneficiary
        fields = [
            'id', 'lokos_shg_code', 'lokos_member_code', 'member_name', 'age',
            'gender', 'designation', 'pldstatus', 'socialcategory', 'religion',
            'mobile', 'email', 'education', 'address', 'district', 'block',
            'panchayat', 'village', 'remarks', 'attended', 'isreplaced', 'registeredon'
        ]

# ----------------------------
# Batch Nested Serializers (CORRECT related_names from models)
# ----------------------------

class BatchReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    centre = TrainingPartnerCentreReportSerializer(read_only=True)
    rooms = TrainingPartnerCentreRoomsReportSerializer(source='centre__rooms', many=True, read_only=True)
    centre_media = TrainingPartnerSubmissionReportSerializer(source='centre__submissions', many=True, read_only=True)
    master_trainers = MasterTrainerReportSerializer(source='batchmastertrainer_set', many=True, read_only=True)

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.Batch
        fields = [
            'id', 'centre', 'rooms', 'centre_media', 'master_trainers',
            'batchtype', 'code', 'status', 'startdate', 'enddate', 'timeoftraining'
        ]

class BatchScheduleReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchSchedule
        fields = ['id', 'scheduledate', 'starttime', 'remarks']

class BatchMasterTrainerReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    master_trainer = MasterTrainerReportSerializer(read_only=True)
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchMasterTrainer
        fields = ['id', 'master_trainer', 'participated', 'status', 'remarks']

class BatchBeneficiaryReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    beneficiary = TRBeneficiaryReportSerializer(read_only=True)
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchBeneficiary
        fields = ['id', 'beneficiary', 'registeredon', 'attended', 'isreplaced']

class BatchTrainerReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    trainer = MasterTrainerReportSerializer(read_only=True)
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchTrainer
        fields = ['id', 'trainer', 'registeredon', 'attended', 'isreplaced']

class BatchEkycVerificationReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchEkycVerification
        fields = ['id', 'participantid', 'participantrole', 'ekycstatus', 'ekycdocument', 'verifiedon', 'remarks']

class BatchAttendanceReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    csv_upload = serializers.FileField(source='csvupload')
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchAttendance
        fields = ['id', 'date', 'csv_upload']

class ParticipantAttendanceReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.ParticipantAttendance
        fields = ['id', 'participantid', 'participantname', 'participantrole', 'present']

class TPBatchCostBreakupReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TPBatchCostBreakup
        fields = ['id', 'centrecost', 'hostelcost', 'foodingcost', 'dressescost', 'studymaterialcost', 'totalcost']

class BatchCostReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    trainer_past_cost = serializers.DecimalField(source='trainerpartcost', max_digits=12, decimal_places=2)
    tp_part_cost = serializers.DecimalField(source='tppartcost', max_digits=12, decimal_places=2)
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchCost
        fields = ['id', 'trainer_past_cost', 'tp_part_cost']

class BatchMediaReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.BatchMedia
        fields = ['id', 'date', 'category', 'file', 'notes']

class TRClosureReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TRClosure
        fields = ['id', 'hra', 'tada']

# ----------------------------
# FINAL TrainingRequestReportSerializer - NO prefetch_related needed
# ----------------------------

class TrainingRequestReportSerializer(SoftDeleteModelSerializer):
    id = serializers.IntegerField(source='id')
    training_plan = TrainingPlanReportSerializer(read_only=True, source='trainingplan')
    partner = TrainingPartnerReportSerializer(read_only=True)
    district = MasterDistrictReportSerializer(read_only=True)
    block = MasterBlockReportSerializer(read_only=True)
    
    # Batch collections - using correct reverse relationships
    batch = serializers.SerializerMethodField()
    batch_schedule = serializers.SerializerMethodField()
    batch_master_trainer = serializers.SerializerMethodField()
    beneficiaries_in_batch = serializers.SerializerMethodField()
    trainers_in_batch = serializers.SerializerMethodField()
    batch_ekyc_participants = serializers.SerializerMethodField()
    batch_attendance_csv = serializers.SerializerMethodField()
    batch_participant_attendance = serializers.SerializerMethodField()
    batch_cost_breakup = serializers.SerializerMethodField()
    batch_overall_cost = serializers.SerializerMethodField()
    batch_media = serializers.SerializerMethodField()
    closure_docs = TRClosureReportSerializer(source='trclosure_set', many=True, read_only=True)

    class Meta(SoftDeleteModelSerializer.Meta):
        model = tms_models.TrainingRequest
        fields = [
            'id', 'training_plan', 'partner', 'trainingtype', 'level', 'status',
            'district', 'block', 'batch', 'batch_schedule', 'batch_master_trainer',
            'beneficiaries_in_batch', 'trainers_in_batch', 'batch_ekyc_participants',
            'batch_attendance_csv', 'batch_participant_attendance', 'batch_cost_breakup',
            'batch_overall_cost', 'batch_media', 'closure_docs'
        ]

    def get_batch(self, obj):
        return BatchReportSerializer(
            tms_models.Batch.objects.filter(request=obj.id, is_active=True), many=True, context=self.context
        ).data

    def get_batch_schedule(self, obj):
        return BatchScheduleReportSerializer(
            tms_models.BatchSchedule.objects.filter(batch__request=obj.id, is_active=True), many=True, context=self.context
        ).data

    def get_batch_master_trainer(self, obj):
        return BatchMasterTrainerReportSerializer(
            tms_models.BatchMasterTrainer.objects.filter(batch__request=obj.id, is_active=True), many=True, context=self.context
        ).data

    def get_beneficiaries_in_batch(self, obj):
        return BatchBeneficiaryReportSerializer(
            tms_models.BatchBeneficiary.objects.filter(batch__request=obj.id, is_active=True), many=True, context=self.context
        ).data

    def get_trainers_in_batch(self, obj):
        return BatchTrainerReportSerializer(
            tms_models.BatchTrainer.objects.filter(batch__request=obj.id, is_active=True), many=True, context=self.context
        ).data

    def get_batch_ekyc_participants(self, obj):
        return BatchEkycVerificationReportSerializer(
            tms_models.BatchEkycVerification.objects.filter(batch__request=obj.id, is_active=True), many=True, context=self.context
        ).data

    def get_batch_attendance_csv(self, obj):
        return BatchAttendanceReportSerializer(
            tms_models.BatchAttendance.objects.filter(batch__request=obj.id, is_active=True), many=True, context=self.context
        ).data

    def get_batch_participant_attendance(self, obj):
        return ParticipantAttendanceReportSerializer(
            tms_models.ParticipantAttendance.objects.filter(attendance__batch__request=obj.id, is_active=True), many=True, context=self.context
        ).data

    def get_batch_cost_breakup(self, obj):
        return TPBatchCostBreakupReportSerializer(
            tms_models.TPBatchCostBreakup.objects.filter(batch__request=obj.id, is_active=True), many=True, context=self.context
        ).data

    def get_batch_overall_cost(self, obj):
        return BatchCostReportSerializer(
            tms_models.BatchCost.objects.filter(batch__request=obj.id, is_active=True), many=True, context=self.context
        ).data

    def get_batch_media(self, obj):
        return BatchMediaReportSerializer(
            tms_models.BatchMedia.objects.filter(batch__request=obj.id, is_active=True), many=True, context=self.context
        ).data