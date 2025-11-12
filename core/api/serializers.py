from rest_framework import serializers
from core.models import MasterUser

class MasterUserSerializer(serializers.ModelSerializer):
    role_name = serializers.SerializerMethodField()

    class Meta:
        model = MasterUser
        fields = ['id', 'username', 'role', 'role_name', 'recovery_mobile', 'TH_urid']

    def get_role_name(self, obj):
        try:
            return obj.role.name if obj.role else None
        except Exception:
            return None