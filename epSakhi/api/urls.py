# epSakhi/api/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    CRPEPViewSet, CRPPanchayatMappingViewSet,
    BeneficiaryRecordedViewSet, ExistingEnterpriseViewSet, NewEnterpriseViewSet,
    UpsrlmShgListView, UpsrlmShgMembersView, UpsrlmShgDetailView
)

router = DefaultRouter()
router.register('crp', CRPEPViewSet, basename='crp')
router.register('recorded-beneficiaries', BeneficiaryRecordedViewSet, basename='recorded-beneficiaries')
router.register('existing-enterprise', ExistingEnterpriseViewSet, basename='existing-enterprise')
router.register('new-enterprise', NewEnterpriseViewSet, basename='new-enterprise')

mapping_urls = [
    path('crp/<int:pk>/link-panchayats/', CRPPanchayatMappingViewSet.as_view({'post':'link'}), name='crp-link-panchayats'),
]

urlpatterns = [
    path('', include(router.urls)),
    *mapping_urls,
    path('upsrlm-shg-list/<int:block_id>/', UpsrlmShgListView.as_view(), name='upsrlm-shg-list'),
    path('upsrlm-shg-members/<str:shg_code>/', UpsrlmShgMembersView.as_view(), name='upsrlm-shg-members'),
    path('upsrlm-shg-detail/<str:shg_code>/', UpsrlmShgDetailView.as_view(), name='upsrlm-shg-detail'),
]
