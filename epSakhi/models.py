# epSakhi/models.py
import uuid
from django.db import models
from django.utils import timezone
from core.models import (
    MasterUser,
    MasterPanchayat,
    MasterShgList,
    MasterBeneficiary,
    MasterClfList,
    MasterDistrict,
    MasterBlock,
)

class SoftDeleteMixin(models.Model):
    """
    Global fields applied to all epSakhi models:
      - created_by / updated_by / deleted_by -> FK to core.MasterUser
      - created_at / updated_at / deleted_at -> timestamps
      - is_active -> soft-delete flag (True = active)
      - TH_urid -> unique UUID string per row
    Also provides soft delete behaviour via delete() method.
    """
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    deleted_at = models.DateTimeField(null=True, blank=True, db_column='deleted_at')

    # Track who created/updated/deleted the row. Use SET_NULL so user deletion does not remove rows.
    created_by = models.ForeignKey(
        'core.MasterUser',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='created_by',
        related_name='+',
        db_constraint=False
    )
    updated_by = models.ForeignKey(
        'core.MasterUser',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='updated_by',
        related_name='+',
        db_constraint=False
    )
    deleted_by = models.ForeignKey(
        'core.MasterUser',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='deleted_by',
        related_name='+',
        db_constraint=False
    )

    is_active = models.BooleanField(default=True, db_column='is_active')
    TH_urid = models.CharField(max_length=36, default=uuid.uuid4, editable=False, db_column='TH_urid')

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, by_user: MasterUser = None):
        """
        Soft delete: set deleted_at and is_active=False and if by_user provided set deleted_by.
        Call with instance.delete(by_user=some_master_user_instance) to record deleter.
        """
        self.deleted_at = timezone.now()
        self.is_active = False
        if by_user is not None:
            try:
                # Accept either MasterUser instance or integer id
                if isinstance(by_user, MasterUser):
                    self.deleted_by = by_user
                else:
                    # allow passing an id
                    self.deleted_by_id = int(by_user)
            except Exception:
                # ignore if mapping fails
                pass
        self.save()

    def hard_delete(self):
        super().delete()

# -------------------------
# epSakhi models (use mixin)
# -------------------------

class CRPEP(SoftDeleteMixin):
    id = models.BigAutoField(primary_key=True)

    district = models.ForeignKey(
        'core.MasterDistrict',
        on_delete=models.PROTECT,
        db_column='district_id',
        db_constraint=False
    )
    block = models.ForeignKey(
        'core.MasterBlock',
        on_delete=models.PROTECT,
        db_column='block_id',
        db_constraint=False
    )
    gram_panchayat = models.ForeignKey(
        'core.MasterPanchayat',
        on_delete=models.PROTECT,
        db_column='panchayat_id',
        db_constraint=False
    )

    master_user = models.ForeignKey(
        'core.MasterUser',
        on_delete=models.PROTECT,
        db_column='user_id',
        related_name='crpep_account',
        null=True,
        blank=True,
        db_constraint=False
    )

    name = models.CharField(max_length=255)
    shg = models.ForeignKey(
        'core.MasterShgList',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column='shg_code',
        to_field='shg_code',
        db_constraint=False
    )

    nodal_clf = models.ForeignKey(
        'core.MasterClfList',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='clf_nodal',
        db_column='clf_code',
        to_field='clf_code',
        db_constraint=False
    )

    CATEGORY_CHOICES = [
        ('GENERAL', 'General'),
        ('OBC', 'OBC'),
        ('SC', 'SC'),
        ('ST', 'ST'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, null=True, blank=True)
    subcategory = models.CharField(max_length=100, null=True, blank=True)
    marks_obtained = models.IntegerField(null=True, blank=True)
    mobile_number = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = 'epSakhi_crpep'

    def __str__(self):
        return f"{self.id} - {self.name}"


class BeneficiaryEnterprise(SoftDeleteMixin):
    # --------------------------------------------------
    # Primary & Foreign Keys
    # --------------------------------------------------
    id = models.BigAutoField(primary_key=True)
    beneficiary = models.ForeignKey(
        'core.MasterBeneficiary',
        on_delete=models.PROTECT,
        db_column='beneficiary_id',
        to_field='member_code',
        db_constraint=False
    )

    # recorded_by_user is a domain-specific field (who recorded this enterprise).
    recorded_by_user = models.ForeignKey(
        'core.MasterUser',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='recorded_by_user_id',
        related_name='recorded_enterprises',
        db_constraint=False
    )

    # --------------------------------------------------
    # 1. Existing Enterprise Details
    # --------------------------------------------------
    has_existing_enterprise = models.BooleanField(default=False)
    existing_enterprise_name = models.CharField(max_length=255, null=True, blank=True)
    activity_or_product_type = models.CharField(max_length=255, null=True, blank=True)
    establishment_year_existing = models.IntegerField(null=True, blank=True)
    business_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Manufacturing / Service / Trading / Other"
    )
    monthly_income_estimate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    number_of_employees = models.PositiveIntegerField(null=True, blank=True)
    sales_area = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Local / District / Online / Other"
    )
    received_any_scheme_support = models.BooleanField(default=False)
    scheme_support_details = models.TextField(null=True, blank=True)

    # --------------------------------------------------
    # 2. For Non-Entrepreneurs (Interest in Starting)
    # --------------------------------------------------
    interested_in_starting_enterprise = models.BooleanField(default=False)
    interested_business_type = models.CharField(max_length=255, null=True, blank=True)
    location_identified = models.BooleanField(default=False)
    any_training_taken = models.BooleanField(default=False)
    training_details = models.TextField(null=True, blank=True)

    # --------------------------------------------------
    # 3. Existing Enterprise (Detailed Business Profile)
    # --------------------------------------------------
    enterprise_name = models.CharField(max_length=255)
    enterprise_type = models.CharField(max_length=255, null=True, blank=True)
    ownership_type = models.CharField(max_length=255, null=True, blank=True)
    year_of_establishment = models.IntegerField(null=True, blank=True)
    raw_material = models.TextField(null=True, blank=True)
    machinery_equipment = models.TextField(null=True, blank=True)
    workplace_type = models.CharField(max_length=255, null=True, blank=True)
    electricity_available = models.BooleanField(default=False)
    water_available = models.BooleanField(default=False)
    transportation_facility = models.CharField(max_length=255, null=True, blank=True)
    initial_investment = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    source_of_investment = models.CharField(max_length=255, null=True, blank=True)
    working_capital_monthly = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    annual_turnover = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    profit_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    loan_details = models.TextField(null=True, blank=True)
    main_product_service = models.TextField(null=True, blank=True)
    product_features = models.TextField(null=True, blank=True)
    production_capacity = models.CharField(max_length=255, null=True, blank=True)
    packaging_branding_status = models.CharField(max_length=255, null=True, blank=True)
    certification_registration = models.CharField(max_length=255, null=True, blank=True)
    target_customers = models.TextField(null=True, blank=True)
    marketing_channels = models.TextField(null=True, blank=True)
    monthly_sales = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    marketing_strategy = models.TextField(null=True, blank=True)
    marketing_challenges = models.TextField(null=True, blank=True)
    training_received = models.TextField(null=True, blank=True)
    skills_acquired = models.TextField(null=True, blank=True)
    future_training_requirements = models.TextField(null=True, blank=True)
    institutional_support = models.TextField(null=True, blank=True)
    financial_coordination = models.TextField(null=True, blank=True)
    market_linkage = models.TextField(null=True, blank=True)
    mentorship_support = models.TextField(null=True, blank=True)
    expansion_plan = models.TextField(null=True, blank=True)
    required_support = models.TextField(null=True, blank=True)

    # --------------------------------------------------
    # 4. Support Required from UPSRLM
    # --------------------------------------------------
    support_skill_training = models.BooleanField(default=False)
    support_entrepreneurship_training = models.BooleanField(default=False)
    support_financial_assistance = models.BooleanField(default=False)
    support_market_branding = models.BooleanField(default=False)
    support_infrastructure = models.BooleanField(default=False)
    support_digital_emarket = models.BooleanField(default=False)
    support_other = models.BooleanField(default=False)
    support_other_details = models.TextField(null=True, blank=True)

    # --------------------------------------------------
    # 5. Photos & Documents
    # --------------------------------------------------
    photo_enterprise = models.ImageField(upload_to='epSakhi/enterprise_photos/%Y/%m/', null=True, blank=True)
    photo_entrepreneur = models.ImageField(upload_to='epSakhi/beneficiary_photos/%Y/%m/', null=True, blank=True)
    photo_product = models.ImageField(upload_to='epSakhi/product_photos/%Y/%m/', null=True, blank=True)
    certificate_docs = models.FileField(upload_to='epSakhi/certificates/%Y/%m/', null=True, blank=True)

    # --------------------------------------------------
    # 6. Declaration Section
    # --------------------------------------------------
    declaration_confirmed = models.BooleanField(default=False)
    declaration_date = models.DateField(null=True, blank=True)
    verifier_name = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'epSakhi_beneficiary_enterprise'

    def __str__(self):
        return f"{self.id} - {self.enterprise_name}"


class CRPEPToPanchayat(SoftDeleteMixin):
    id = models.BigAutoField(primary_key=True)
    crp = models.ForeignKey(CRPEP, on_delete=models.CASCADE, db_column='crp_id', db_constraint=False)
    allocated_panchayat_id = models.BigIntegerField()

    class Meta:
        db_table = 'epSakhi_crpep_panchayat'

    def __str__(self):
        return f"{self.crp_id} -> {self.allocated_panchayat_id}"
