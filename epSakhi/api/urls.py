# epSakhi/api/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import CRPEPViewSet, CRPPanchayatMappingViewSet, BeneficiaryEnterpriseViewSet

router = DefaultRouter()
router.register('crp', CRPEPViewSet, basename='crp')
router.register('enterprise', BeneficiaryEnterpriseViewSet, basename='enterprise')

mapping_urls = [
    path('crp/<int:pk>/link-panchayats/', CRPPanchayatMappingViewSet.as_view({'post':'link'}), name='crp-link-panchayats'),
]

urlpatterns = [
    path('', include(router.urls)),
    *mapping_urls,
]
