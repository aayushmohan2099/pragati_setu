# core/api/auth_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from core.models import MasterUser
from .serializers import MasterUserSerializer

class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return Response({'detail':'username and password required'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=username, password=password)
        if not user:
            return Response({'detail':'invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        try:
            mu = MasterUser.objects.get(username=user.username)
        except MasterUser.DoesNotExist:
            return Response({'detail': 'master user missing'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        s = MasterUserSerializer(mu)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': s.data
        })

class CRPRequestOtpView(APIView):
    permission_classes = (permissions.AllowAny,)
    def post(self, request):
        return Response({'detail':'OTP feature currently disabled (placeholder).'}, status=status.HTTP_200_OK)

class CRPVerifyOtpView(APIView):
    permission_classes = (permissions.AllowAny,)
    def post(self, request):
        return Response({'detail':'OTP verification disabled (placeholder).'}, status=status.HTTP_200_OK)
