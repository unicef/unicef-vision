from django.conf import settings

# Timeout settings defaults to 400 secods or 5 min
TIMEOUT = settings.INSIGHT_REQUESTS_TIMEOUT if hasattr(settings, "INSIGHT_REQUESTS_TIMEOUT") else 400
INSIGHT_DATE_FORMAT = settings.INSIGHT_DATE_FORMAT if hasattr(settings, "INSIGHT_DATE_FORMAT") else "%d-%b-%y"
