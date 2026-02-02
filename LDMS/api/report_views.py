# LDMS/api/report_views.py
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response

from django.db.models import F

from LDMS.models import recorded_benefs
from core.models import (
    MasterBlock,
    MasterDistrictCategoryMapping,
)


class RecordedBeneficiaryReportViewSet(ViewSet):
    """
    REPORT API for Recorded Beneficiaries
    - ONLY APPROVED support buckets
    - Fully denormalized
    - Supports complex filter combinations
    - Optimized for Excel export
    - NO serializer (intentional)
    """

    def list(self, request):
        params = request.query_params

        qs = (
            recorded_benefs.objects
            .select_related(
                "district_id",
                "block_id",
                "panchayat_id",
                "village_id",
                "support_bucket__department",
                "support_bucket__scheme",
                "support_bucket__bucket_type",
            )
            .prefetch_related(
                "support_bucket__trainingsupport_set",
                "support_bucket__bucket_approval_set",
            )
            # ✅ CRITICAL FILTER: ONLY APPROVED BUCKETS
            .filter(
                support_bucket__bucket_approval__approval_status="APPROVED"
            )
        )

        # =====================================================
        # 1️⃣ GEOGRAPHICAL FILTERS
        # =====================================================
        mandal_id = params.get("mandal_id")
        dc_id = params.get("dc_id")
        district_id = params.get("district_id")
        block_id = params.get("block_id")
        panchayat_id = params.get("panchayat_id")

        if mandal_id:
            block_ids = MasterBlock.objects.filter(
                district__mandal_id=mandal_id
            ).values_list("block_id", flat=True)
            qs = qs.filter(block_id__in=block_ids)

        if dc_id:
            district_ids = MasterDistrictCategoryMapping.objects.filter(
                category_id=dc_id
            ).values_list("district_id", flat=True)

            block_ids = MasterBlock.objects.filter(
                district_id__in=district_ids
            ).values_list("block_id", flat=True)

            qs = qs.filter(block_id__in=block_ids)

        if district_id:
            qs = qs.filter(district_id=district_id)

        if block_id:
            qs = qs.filter(block_id=block_id)

        if panchayat_id:
            qs = qs.filter(panchayat_id=panchayat_id)

        # =====================================================
        # 2️⃣ DEPARTMENT FILTER
        # =====================================================
        department_id = params.get("department_id")
        if department_id:
            qs = qs.filter(
                support_bucket__department_id=department_id
            )

        # =====================================================
        # 3️⃣ SCHEME FILTERS
        # =====================================================
        scheme_id = params.get("scheme_id")
        scheme_code = params.get("scheme_code")
        scope = params.get("scope")
        funding = params.get("funding")
        contact_point = params.get("contact_point")

        if scheme_id:
            qs = qs.filter(support_bucket__scheme_id=scheme_id)

        if scheme_code:
            qs = qs.filter(
                support_bucket__scheme__code__icontains=scheme_code
            )

        if scope:
            qs = qs.filter(
                support_bucket__scheme__scope__icontains=scope
            )

        if funding:
            qs = qs.filter(
                support_bucket__scheme__funding__icontains=funding
            )

        if contact_point:
            qs = qs.filter(
                support_bucket__scheme__contact_point__icontains=contact_point
            )

        # =====================================================
        # 4️⃣ RECORDED BENEFICIARY FILTERS
        # =====================================================
        for field in [
            "pld_status",
            "designation",
            "gender",
            "religion",
            "marital_status",
            "social_category",
        ]:
            value = params.get(field)
            if value:
                qs = qs.filter(**{field: value})

        # =====================================================
        # 5️⃣ SUPPORT BUCKET TYPE
        # =====================================================
        bucket_type = params.get("bucket_type")
        if bucket_type:
            qs = qs.filter(
                support_bucket__bucket_type__bucket_type__iexact=bucket_type
            )

        # =====================================================
        # 6️⃣ TRAINING SUPPORT FILTERS
        # =====================================================
        training_theme = params.get("training_theme")
        training_plan = params.get("training_plan")

        if training_theme:
            qs = qs.filter(
                support_bucket__trainingsupport__training_theme_id=training_theme
            )

        if training_plan:
            qs = qs.filter(
                support_bucket__trainingsupport__training_plan_id=training_plan
            )

        # =====================================================
        # 🔚 FINAL DENORMALIZED OUTPUT
        # =====================================================
        data = qs.values(
            # --- Beneficiary ---
            "lokos_shg_code",
            "lokos_member_code",
            "pld_status",
            "member_name",
            "designation",
            "gender",
            "religion",
            "marital_status",
            "father_husband_name",
            "social_category",
            "education",
            "address",
            "mobile",
            "age",

            # --- Geography ---
            district_name_en=F("district_id__district_name_en"),
            block_name_en=F("block_id__block_name_en"),
            panchayat_name_en=F("panchayat_id__panchayat_name_en"),
            village_name_english=F("village_id__village_name_english"),

            # --- Department ---
            department_name=F("support_bucket__department__name"),

            # --- Scheme ---
            scheme_name=F("support_bucket__scheme__name"),
            scheme_code=F("support_bucket__scheme__code"),

            # --- Support Bucket ---
            bucket_type=F("support_bucket__bucket_type__bucket_type"),
            benefit_name=F("support_bucket__benefit_name"),
            benefit_description=F("support_bucket__benefit_description"),

            # --- Training ---
            training_theme=F(
                "support_bucket__trainingsupport__training_theme__theme_name"
            ),
            training_plan=F(
                "support_bucket__trainingsupport__training_plan__training_name"
            ),

            # --- Approval ---
            approval_status=F(
                "support_bucket__bucket_approval__approval_status"
            ),
            approval_date=F(
                "support_bucket__bucket_approval__approval_date"
            ),
            approved_by=F(
                "support_bucket__bucket_approval__approved_by__username"
            ),
        )

        return Response(list(data))
