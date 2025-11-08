# epSakhi/admin.py
from django.contrib import admin
from .models import CRPEP, BeneficiaryEnterprise

@admin.register(CRPEP)
class CRPEPAdmin(admin.ModelAdmin):
    list_display = ['id','name','mobile_number','district','block','gram_panchayat','created_at']
    search_fields = ['name','mobile_number']
    readonly_fields = ['created_at','updated_at','deleted_at','TH_urid']

@admin.register(BeneficiaryEnterprise)
class BeneficiaryEnterpriseAdmin(admin.ModelAdmin):
    list_display = ['id','enterprise_name','beneficiary','recorded_by_user','created_at']
    search_fields = ['enterprise_name']
    readonly_fields = ['created_at','updated_at','deleted_at','TH_urid']
