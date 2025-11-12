# pragati_setu/middleware.py
"""
API header / JWT-aware middleware.

Rules implemented:
- Allow all non-API paths through.
- Allow all /api/v1/auth/* (login / otp) without headers (these must remain accessible).
- Require X-API-ID / X-API-KEY ONLY for core master-data lookup endpoints:
    -> paths starting with /api/v1/lookups/
- For other /api/ endpoints (e.g. epSakhi APIs), require a valid JWT access token in Authorization:
    -> If Authorization Bearer token valid -> check MasterUser.role id is allowed for epSakhi.
    -> Allowed epSakhi role ids: 1,2,3,10,6,8,9
- Existing behavior for header-checking on lookups is preserved.
- We keep responses JSON and status 401 for missing/invalid credentials.
"""

import json
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

# SimpleJWT token class for validation
from rest_framework_simplejwt.tokens import AccessToken, TokenError

# Import MasterUser for role checks
from core.models import MasterUser

API_ID_HEADER = "HTTP_X_API_ID"   # Django WSGI prefix mapping for X-API-ID
API_KEY_HEADER = "HTTP_X_API_KEY"

# Which roles are allowed to access epSakhi APIs (master_user.role id)
EP_SAKHI_ALLOWED_ROLE_IDS = {1, 2, 3, 10, 6, 8, 9}

class ApiIdApiKeyMiddleware(MiddlewareMixin):
    """
    Middleware that:
    - Enforces X-API headers for core lookups endpoints.
    - Allows auth endpoints without headers.
    - Requires valid JWT with allowed role ids for other /api/ endpoints (epSakhi).
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.get_response = get_response
        # allowed credentials map (api_id -> api_key)
        self.allowed = getattr(settings, 'ALLOWED_API_CREDENTIALS', {})

    def _check_api_headers(self, request):
        api_id = request.META.get(API_ID_HEADER)
        api_key = request.META.get(API_KEY_HEADER)
        if not api_id or not api_key:
            return False, 'Missing X-API-ID or X-API-KEY headers'
        expected = self.allowed.get(api_id)
        if not expected or api_key != expected:
            return False, 'Invalid API credentials'
        return True, None

    def _validate_access_token_and_role(self, request):
        """
        Validate Authorization: Bearer <token>
        If token valid, ensure corresponding MasterUser exists, is active and role id is allowed.
        Return (True, None) if ok; else (False, reason)
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header:
            return False, 'Missing Authorization header'
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return False, 'Invalid Authorization header format'

        token_str = parts[1]
        try:
            # Validate token signature and expiry
            access = AccessToken(token_str)
        except TokenError as e:
            return False, 'Invalid or expired access token'

        # Token validated — extract user id
        # SimpleJWT standard claim: 'user_id'
        user_id = access.payload.get('user_id') or access.payload.get('user_id')
        if not user_id:
            return False, 'Access token missing user_id'

        try:
            # MasterUser.id is BigAutoField; token user id may be str or int
            mu = MasterUser.objects.get(id=int(user_id))
        except Exception:
            return False, 'Master user not found'

        # check active flag
        try:
            if not getattr(mu, 'is_active', 0):
                return False, 'User inactive'
        except Exception:
            # be conservative
            return False, 'User inactive/invalid'

        # check role id presence and allowed list
        try:
            role_val = None
            # MasterUser.role is FK -> MasterRoles; role.id is integer
            if getattr(mu, 'role', None):
                role_val = getattr(mu.role, 'id', None)
            # In some DB shapes role might be stored as integer in field 'role' - handle that
            if role_val is None:
                # try to read raw int (fallback)
                role_val = getattr(mu, 'role_id', None) or getattr(mu, 'role', None)
            if role_val is None:
                return False, 'User role missing'
            # cast to int for comparison
            role_id_int = int(role_val)
        except Exception:
            return False, 'Error reading user role'

        if role_id_int not in EP_SAKHI_ALLOWED_ROLE_IDS:
            return False, 'User role not authorized for this API'

        # all good
        return True, None

    def process_request(self, request):
        """
        Called early in request cycle. Return JsonResponse on auth failure, else None to continue.
        """
        path = request.path or ''

        # Non-API paths pass through
        if not path.startswith('/api/'):
            return None

        # Keep auth endpoints open (login, crp otp endpoints) so login works without special headers
        if path.startswith('/api/v1/auth/'):
            return None

        # Core master-data lookups require X-API headers (preserve previous behavior)
        if path.startswith('/api/v1/lookups/'):
            ok, reason = self._check_api_headers(request)
            if not ok:
                return JsonResponse({'detail': reason}, status=401)
            return None

        # For all other API endpoints (epSakhi and others) require a valid JWT + allowed role
        ok, reason = self._validate_access_token_and_role(request)
        if not ok:
            return JsonResponse({'detail': reason}, status=401)

        # If everything passes, continue to view / other middlewares
        return None

    def process_response(self, request, response):
        # do not alter responses; just return
        return response
