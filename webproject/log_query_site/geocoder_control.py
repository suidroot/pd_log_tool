import logging
import redis as redis_client
from django.conf import settings

logger = logging.getLogger(__name__)

_PAUSE_KEY = 'geocoder:paused'


def _redis():
    return redis_client.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)


def is_paused() -> bool:
    try:
        return bool(_redis().exists(_PAUSE_KEY))
    except Exception:
        logger.warning("geocoder_control: could not check pause state (Redis unavailable)")
        return False


def pause():
    try:
        _redis().set(_PAUSE_KEY, '1')
    except Exception:
        logger.error("geocoder_control: could not set pause flag (Redis unavailable)")


def resume():
    try:
        _redis().delete(_PAUSE_KEY)
    except Exception:
        logger.error("geocoder_control: could not clear pause flag (Redis unavailable)")
