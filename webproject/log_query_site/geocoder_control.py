import redis as redis_client
from django.conf import settings

_PAUSE_KEY = 'geocoder:paused'


def _redis():
    return redis_client.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)


def is_paused() -> bool:
    try:
        return bool(_redis().exists(_PAUSE_KEY))
    except Exception:
        return False


def pause():
    _redis().set(_PAUSE_KEY, '1')


def resume():
    _redis().delete(_PAUSE_KEY)
