from django.apps import apps
from django.conf import settings

import requests

from unicef_vision.settings import TIMEOUT

base_headers = {
    "Content-Type": "application/json",
    "Ocp-Apim-Subscription-Key": settings.INSIGHT_SUB_KEY,
}


def get_vision_logger_domain_model():
    get_model = apps.get_model
    return get_model(settings.INSIGHT_LOGGER_MODEL)


def get_data_from_insight(endpoint, data=None):
    separator = "" if settings.INSIGHT_URL.endswith("/") else "/"

    if not data:
        data = {}

    url = "{}{}{}".format(settings.INSIGHT_URL, separator, endpoint).format(**data)

    resp = requests.get(url, headers=base_headers, timeout=TIMEOUT)
    if resp.status_code != 200:
        return False, "Loading data from Vision Failed, status {}".format(resp.status_code)
    try:
        result = resp.json()
    except ValueError:
        return (
            False,
            "Loading data from Vision Failed, no valid response returned for data: {}".format(data),
        )
    return True, result


def comp_decimals(y, x):
    def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
        return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

    return isclose(float(x), float(y))
