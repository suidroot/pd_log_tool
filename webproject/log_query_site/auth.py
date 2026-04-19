import hashlib
from functools import wraps

from django.http import JsonResponse
from django.utils import timezone

from .models import APIKey


def require_api_key(view_func):
    """Authenticate requests using a Bearer API key in the Authorization header."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'API key required'}, status=401)

        raw_key = auth_header[len('Bearer '):]
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        try:
            api_key = APIKey.objects.get(key_hash=key_hash, is_active=True)
        except APIKey.DoesNotExist:
            return JsonResponse({'error': 'Invalid or inactive API key'}, status=401)

        api_key.last_used = timezone.now()
        api_key.save(update_fields=['last_used'])

        return view_func(request, *args, **kwargs)

    return wrapper
