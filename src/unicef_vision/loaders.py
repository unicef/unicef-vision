import json
import logging

import requests
from django.conf import settings

from unicef_vision.exceptions import VisionException
from unicef_vision.settings import TIMEOUT
from unicef_vision.utils import base_headers

logger = logging.getLogger(__name__)

INSIGHT_NO_DATA_MESSAGE = 'No Data Available'


class VisionDataLoader:
    """Base class for Data Loading"""

    def __init__(self, endpoint, business_area_code=None, **kwargs):

        self.URL = kwargs.get('url', settings.INSIGHT_URL)
        self.set_headers(kwargs.get('headers', ()))
        self.set_url(endpoint, business_area_code)

    def set_url(self, endpoint, detail):
        separator = '' if self.URL.endswith('/') else '/'

        self.url = '{}{}{}'.format(self.URL, separator, endpoint)
        if detail:
            self.url += '/{}'.format(detail)
        logger.info('About to get data from {}'.format(self.url))

    def set_headers(self, headers):
        self.headers = base_headers
        if headers:
            for header_name, header_value in headers:
                self.headers[header_name] = header_value

    def get(self):
        response = requests.get(
            self.url,
            headers=self.headers,
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            raise VisionException('Load data failed! Http code: {}'.format(response.status_code))
        json_response = response.json()
        if json_response == INSIGHT_NO_DATA_MESSAGE:
            return []

        return json_response


class ManualDataLoader(VisionDataLoader):
    """
    Can be used to sync single objects from INSIGHT url templates:
    /endpoint if no business_area_code or object_number
    /endpoint/business_area_code if no object number provided
    /endpoint/object_number else
    """

    def __init__(self, endpoint, business_area_code=None, object_number=None, **kwargs):
        super().__init__(endpoint, business_area_code, **kwargs)

        if object_number:
            self.set_url(endpoint, object_number)


class FileDataLoader:
    """Loader to read json file instead of REST API"""

    def __init__(self, filename, *args, **kwargs):
        self.filename = filename

    def get(self):
        data = json.load(open(self.filename))
        return data
