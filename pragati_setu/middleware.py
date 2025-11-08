# pragati_setu/middleware.py
import json
from django.conf import settings
from django.http import JsonResponse

API_ID_HEADER = "HTTP_X_API_ID"   # Django WSGI prefix mapping
API_KEY_HEADER = "HTTP_X_API_KEY"

class ApiIdApiKeyMiddleware:
    """
    Enforce that requests under /api/ include X-API-ID and X-API-KEY
    and that the pair exists in settings.ALLOWED_API_CREDENTIALS.
    Non-API requests are passed through.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed = getattr(settings, 'ALLOWED_API_CREDENTIALS', {})

    def __call__(self, request):
        path = request.path or ''
        if path.startswith('/api/'):
            api_id = request.META.get(API_ID_HEADER)
            api_key = request.META.get(API_KEY_HEADER)
            if not api_id or not api_key:
                return JsonResponse({'detail': 'Missing X-API-ID or X-API-KEY headers'}, status=401)
            expected = self.allowed.get(api_id)
            if not expected or api_key != expected:
                return JsonResponse({'detail': 'Invalid API credentials'}, status=401)
        return self.get_response(request)
