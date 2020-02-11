from django.conf import settings

# Timeout settings defaults to 400 secods or 5 min
TIMEOUT = settings.VISION_REQUESTS_TIMEOUT if hasattr(settings, "VISION_REQUESTS_TIMEOUT") else 400
