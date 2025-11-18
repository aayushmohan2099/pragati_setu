from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import (
    CRPEPViewSet,
    CRPPanchayatMappingViewSet,
    BeneficiaryRecordedViewSet,
    ExistingEnterpriseViewSet,
    NewEnterpriseViewSet,
    UpsrlmShgListView,
    UpsrlmShgMembersView,
    UpsrlmShgDetailView,
    # NEW epSakhi APIs
    CRPListByClfView,
    CRPDetailView,
    CRPPanchayatsUnderCrpView,
    EpsakhiListByShgView,
    EpsakhiDetailByMemberView,
    CRPDetailbyUserID,
    CRPPanchayatsUnderCrpByID,
    # NEW: child enterprise viewsets
    EnterpriseLoanDetailViewSet,
    EnterpriseSupportDetailViewSet,
    EnterpriseTrainingReqViewSet,
    EnterpriseMediaViewSet,
)

router = DefaultRouter()
router.register('crp', CRPEPViewSet, basename='crp')
router.register('recorded-beneficiaries', BeneficiaryRecordedViewSet, basename='recorded-beneficiaries')
router.register('existing-enterprise', ExistingEnterpriseViewSet, basename='existing-enterprise')
router.register('new-enterprise', NewEnterpriseViewSet, basename='new-enterprise')

# NEW: child table routers
router.register('enterprise-loan-details', EnterpriseLoanDetailViewSet, basename='enterprise-loan-details')
router.register('enterprise-support-details', EnterpriseSupportDetailViewSet, basename='enterprise-support-details')
router.register('enterprise-training-reqs', EnterpriseTrainingReqViewSet, basename='enterprise-training-reqs')
router.register('enterprise-media', EnterpriseMediaViewSet, basename='enterprise-media')

mapping_urls = [
    path(
        'crp/<int:pk>/link-panchayats/',
        CRPPanchayatMappingViewSet.as_view({'post': 'link'}),
        name='crp-link-panchayats',
    ),
]

custom_urls = [
    # CRP helper APIs
    path('crp-list/<str:clf_code>/', CRPListByClfView.as_view(), name='crp-list-by-clf'),
    path('crp-detail/<str:member_code>/', CRPDetailView.as_view(), name='crp-detail-by-member'),
    path('crp-detail/id/<str:id>/', CRPDetailbyUserID.as_view(), name='crp-detail-by-user'),
    path(
        'panchayats-under-crp/id/<str:id>/',
        CRPPanchayatsUnderCrpByID.as_view(),
        name='panchayats-under-crp-id',
    ),
    path(
        'panchayats-under-crp/<str:member_code>/',
        CRPPanchayatsUnderCrpView.as_view(),
        name='panchayats-under-crp',
    ),

    # epSakhi recorded-beneficiaries shortcuts
    path('epsakhi-list/<str:shg_code>/', EpsakhiListByShgView.as_view(), name='epsakhi-list'),
    path('epsakhi-detail/<str:member_code>/', EpsakhiDetailByMemberView.as_view(), name='epsakhi-detail'),
]

urlpatterns = [
    path('', include(router.urls)),
    *mapping_urls,
    *custom_urls,
    path('upsrlm-shg-list/<int:block_id>/', UpsrlmShgListView.as_view(), name='upsrlm-shg-list'),
    path('upsrlm-shg-members/<str:shg_code>/', UpsrlmShgMembersView.as_view(), name='upsrlm-shg-members'),
    path('upsrlm-shg-detail/<str:shg_code>/', UpsrlmShgDetailView.as_view(), name='upsrlm-shg-detail'),
]
