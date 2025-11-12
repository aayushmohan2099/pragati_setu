# core/api/auth_urls.py
from django.urls import path
from . import auth_views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('refresh/', auth_views.RefreshTokenView.as_view(), name='token_refresh'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('crp/request-otp/', auth_views.CRPRequestOtpView.as_view(), name='crp_request_otp'),
    path('crp/verify-otp/', auth_views.CRPVerifyOtpView.as_view(), name='crp_verify_otp'),
]
