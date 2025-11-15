# epSakhi/models.py
import uuid
import random
import string
from django.db import models
from django.utils import timezone
from core.models import MasterUser 

def generate_custom_th_urid():
    # Example generator for format like: TH_1AN33KN221 (prefix TH_ + 11 alnum)
    body = ''.join(random.choices(string.ascii_uppercase + string.digits, k=11))
    return f"TH_{body}"

class SoftDeleteMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    deleted_at = models.DateTimeField(null=True, blank=True, db_column='deleted_at')
    created_by = models.ForeignKey(
        'core.MasterUser', null=True, blank=True, on_delete=models.SET_NULL,
        db_column='created_by', related_name='+', db_constraint=False)
    updated_by = models.ForeignKey(
        'core.MasterUser', null=True, blank=True, on_delete=models.SET_NULL,
        db_column='updated_by', related_name='+', db_constraint=False)
    deleted_by = models.ForeignKey(
        'core.MasterUser', null=True, blank=True, on_delete=models.SET_NULL,
        db_column='deleted_by', related_name='+', db_constraint=False)
    is_active = models.BooleanField(default=True, db_column='is_active')

    TH_urid = models.CharField(max_length=36, default=generate_custom_th_urid, editable=False, db_column='TH_urid')

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, by_user: MasterUser = None):
        self.deleted_at = timezone.now()
        self.is_active = False
        if by_user is not None:
            try:
                if isinstance(by_user, MasterUser):
                    self.deleted_by = by_user
                else:
                    self.deleted_by_id = int(by_user)
            except Exception:
                pass
        self.save()

    def hard_delete(self):
        super().delete()


# -------------------------
# CRP Data
# -------------------------
class CRPEP(SoftDeleteMixin):
    id = models.BigAutoField(primary_key=True)

    district_id = models.BigIntegerField(null=True, blank=True, db_column='district_id', db_index=True)
    block_id = models.BigIntegerField(null=True, blank=True, db_column='block_id', db_index=True)
    panchayat_id = models.BigIntegerField(null=True, blank=True, db_column='panchayat_id', db_index=True)

    master_user = models.ForeignKey(
        'core.MasterUser', on_delete=models.PROTECT, db_column='user_id',
        related_name='crpep_account', null=True, blank=True, db_constraint=False)

    name = models.CharField(max_length=255)

    lokos_shg_code = models.CharField(max_length=100, null=True, blank=True, db_column='lokos_shg_code')
 
    nodal_clf = models.BigIntegerField(null=True, blank=True, db_column='nodal_clf')

    lokos_member_code = models.CharField(max_length=100, null=True, blank=True, db_column='lokos_member_code')

    category = models.CharField(max_length=255, null=True, blank=True)

    subcategory = models.CharField(max_length=100, null=True, blank=True)
    marks_obtained = models.IntegerField(null=True, blank=True)
    mobile_number = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = 'epSakhi_crpep'

    def __str__(self):
        return f"{self.id} - {self.name}"


# -------------------------
# New: BeneficiaryRecorded (epSakhi_recorBenefs)
# -------------------------
class BeneficiaryRecorded(SoftDeleteMixin):
    class Meta:
        db_table = 'epSakhi_recorBenefs'

    TH_urid = models.CharField(max_length=36, primary_key=True, default=generate_custom_th_urid, editable=False, db_column='TH_urid')

    lokos_member_code = models.CharField(max_length=100, db_column='lokos_member_code')
    applicant_name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=50, null=True, blank=True)
    marital_status = models.CharField(max_length=50, null=True, blank=True)
    father_husband_name = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    education = models.CharField(max_length=255, null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    district_id = models.BigIntegerField(db_index=True, null=True, blank=True)
    block_id = models.BigIntegerField(db_index=True, null=True, blank=True)
    panchayat_id = models.BigIntegerField(db_index=True, null=True, blank=True)
    village_id = models.BigIntegerField(db_index=True, null=True, blank=True)

    mobile = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    lokos_shg_code = models.CharField(max_length=100, null=True, blank=True)
    # enterprise_id will be FK to whichever enterprise record is created (ExistingEnterprise or NewEnterprise)
    enterprise_id = models.CharField(max_length=100, null=True, blank=True, help_text='TH_urid of enterprise form (existing or new)')

    def __str__(self):
        return f"{self.lokos_member_code} - {self.applicant_name}"


# -------------------------
# ExistingEnterprise + related tables
# -------------------------
class ExistingEnterprise(SoftDeleteMixin):
    TH_urid = models.CharField(max_length=36, primary_key=True, default=generate_custom_th_urid, editable=False, db_column='TH_urid')
    recorded_benef_id = models.CharField(max_length=36, db_column='recorded_benef_id')  
    enterprise_name = models.CharField(max_length=255)
    year_of_establishment = models.IntegerField(null=True, blank=True)
    enterprise_type = models.CharField(max_length=255, null=True, blank=True)
    ownership_type = models.CharField(max_length=255, null=True, blank=True)
    number_of_employees = models.IntegerField(null=True, blank=True)
    activity_or_product_type = models.CharField(max_length=255, null=True, blank=True)
    main_product_name = models.CharField(max_length=255, null=True, blank=True)
    product_features = models.TextField(null=True, blank=True)
    production_capacity = models.CharField(max_length=255, null=True, blank=True)
    raw_material = models.TextField(null=True, blank=True)
    machinery_equipment = models.TextField(null=True, blank=True)
    workplace_type = models.CharField(max_length=255, null=True, blank=True)
    packaging_branding_status = models.CharField(max_length=255, null=True, blank=True)
    certification_registration = models.CharField(max_length=255, null=True, blank=True)
    sales_area = models.CharField(max_length=255, null=True, blank=True)
    monthly_income_estimate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    initial_investment = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    source_of_investment = models.CharField(max_length=255, null=True, blank=True)
    working_capital_monthly = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    annual_turnover = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    profit_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    has_taken_loan = models.BooleanField(default=False)
    financial_coordination = models.TextField(null=True, blank=True)
    target_customers = models.TextField(null=True, blank=True)
    marketing_channels = models.TextField(null=True, blank=True)
    monthly_sales = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    marketing_strategy = models.TextField(null=True, blank=True)
    marketing_challenges = models.TextField(null=True, blank=True)
    electricity_available = models.BooleanField(default=False)
    water_available = models.BooleanField(default=False)
    transportation_facility = models.CharField(max_length=255, null=True, blank=True)
    can_send_to_bijnor_clf = models.BooleanField(default=False)
    need_transport_help = models.BooleanField(default=False)
    has_received_any_scheme_support = models.BooleanField(default=False)
    is_training_received = models.BooleanField(default=False)
    training_details = models.TextField(null=True, blank=True)
    skills_acquired = models.TextField(null=True, blank=True)
    expansion_plan = models.TextField(null=True, blank=True)
    declaration_confirmed = models.BooleanField(default=False)
    declaration_date = models.DateField(null=True, blank=True)
    verifier_name = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'epSakhi_existingEpForm'

    def __str__(self):
        return f"{self.enterprise_name} ({self.TH_urid})"


class EnterpriseLoanDetail(SoftDeleteMixin):
    TH_urid = models.CharField(max_length=36, primary_key=True, default=generate_custom_th_urid, editable=False, db_column='TH_urid')
    enterprise_id = models.CharField(max_length=36, db_column='enterprise_id')  # ExistingEnterprise.TH_urid
    institution_name = models.CharField(max_length=255, null=True, blank=True)
    loan_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    date_taken = models.DateField(null=True, blank=True)
    repayment_status = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'epSakhi_epLoanDeets'


class EnterpriseSupportDetail(SoftDeleteMixin):
    TH_urid = models.CharField(max_length=36, primary_key=True, default=generate_custom_th_urid, editable=False, db_column='TH_urid')
    enterprise_id = models.CharField(max_length=36, db_column='enterprise_id')
    department_name = models.CharField(max_length=255, null=True, blank=True)
    scheme_name = models.CharField(max_length=255, null=True, blank=True)
    date_taken = models.DateField(null=True, blank=True)
    institutional_support = models.BooleanField(default=False)
    mentorship_support = models.BooleanField(default=False)
    required_support = models.BooleanField(default=False)
    what_req_support = models.TextField(null=True, blank=True)
    is_skill_training_needed = models.BooleanField(default=False)
    is_entrepreneurship_training_needed = models.BooleanField(default=False)
    is_financial_assistance_needed = models.BooleanField(default=False)
    is_market_branding_needed = models.BooleanField(default=False)
    is_infrastructure_needed = models.BooleanField(default=False)
    is_digital_emarket_needed = models.BooleanField(default=False)
    other_support = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'epSakhi_epSuppDeets'


class EnterpriseTrainingReq(SoftDeleteMixin):
    TH_urid = models.CharField(max_length=36, primary_key=True, default=generate_custom_th_urid, editable=False, db_column='TH_urid')
    enterprise_id = models.CharField(max_length=36, db_column='enterprise_id')
    skill_name = models.CharField(max_length=255, null=True, blank=True)
    training_type = models.CharField(max_length=255, null=True, blank=True)
    any_specific_scheme = models.CharField(max_length=255, null=True, blank=True)
    any_specific_department = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'epSakhi_epTrainReq'


class EnterpriseMedia(SoftDeleteMixin):
    TH_urid = models.CharField(max_length=36, primary_key=True, default=generate_custom_th_urid, editable=False, db_column='TH_urid')
    enterprise_id = models.CharField(max_length=36, db_column='enterprise_id')
    # store file paths as FileField/ImageField
    photo_entrepreneur = models.ImageField(upload_to='epSakhi/media/%Y/%m/', null=True, blank=True)
    photo_enterprise = models.ImageField(upload_to='epSakhi/media/%Y/%m/', null=True, blank=True)
    open_box_photo = models.ImageField(upload_to='epSakhi/media/%Y/%m/', null=True, blank=True)
    close_box_photo = models.ImageField(upload_to='epSakhi/media/%Y/%m/', null=True, blank=True)
    others = models.ImageField(upload_to='epSakhi/media/%Y/%m/', null=True, blank=True)
    certificates = models.FileField(upload_to='epSakhi/media/%Y/%m/', null=True, blank=True)

    class Meta:
        db_table = 'epSakhi_epMedia'


# -------------------------
# NewEnterprise (for fresh enterprises)
# -------------------------
class NewEnterprise(SoftDeleteMixin):
    TH_urid = models.CharField(max_length=36, primary_key=True, default=generate_custom_th_urid, editable=False, db_column='TH_urid')
    recorded_benef_id = models.CharField(max_length=36, db_column='recorded_benef_id')
    skills_present = models.TextField(null=True, blank=True)
    training_required = models.TextField(null=True, blank=True)
    any_past_experience = models.TextField(null=True, blank=True)
    family_member_ep_details = models.TextField(null=True, blank=True)
    req_skill_training = models.BooleanField(default=False)
    req_ep_development_training = models.BooleanField(default=False)
    req_financial_assistance = models.BooleanField(default=False)
    req_credit_linkage = models.BooleanField(default=False)
    req_market_linkage = models.BooleanField(default=False)
    req_branding = models.BooleanField(default=False)
    req_infra_support = models.BooleanField(default=False)
    req_digi_emarket_linkage = models.BooleanField(default=False)
    declaration_confirmed = models.BooleanField(default=False)
    declaration_date = models.DateField(null=True, blank=True)
    applicant_signature = models.ImageField(upload_to='epSakhi/new_enterprise/%Y/%m/', null=True, blank=True)

    class Meta:
        db_table = 'epSakhi_newEpForm'

    def __str__(self):
        return f"NewEnterprise {self.TH_urid}"
