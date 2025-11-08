# core/api/serializers.py
from rest_framework import serializers
from core.models import MasterUser

class MasterUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterUser
        fields = ['id', 'username', 'role', 'recovery_mobile', 'TH_urid']
