import json
import logging
from urllib.parse import urlencode

import requests
from django.conf import settings

from unicef_vision.exceptions import VisionException
from unicef_vision.settings import TIMEOUT
from unicef_vision.utils import base_headers

logger = logging.getLogger(__name__)

INSIGHT_NO_DATA_MESSAGE = 'No Data Available'


class VisionDataLoader:
    """Base class for Data Loading"""

    def __init__(self, endpoint, detail=None, **kwargs):

        self.URL = kwargs.get('url', settings.INSIGHT_URL)
        self.set_headers(kwargs.get('headers', ()))
        querystring = urlencode(kwargs)
        self.set_url(endpoint, detail, querystring)

    def set_url(self, endpoint, detail, querystring):
        separator = '' if self.URL.endswith('/') else '/'

        self.url = '{}{}{}'.format(self.URL, separator, endpoint)
        if detail:
            self.url += '/{}'.format(detail)
        if querystring:
            self.url += '/?{}'.format(querystring)
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


class FileDataLoader:
    """Loader to read json file instead of REST API"""

    def __init__(self, filename, detail=None, **kwargs):
        self.filename = filename
        self.detail = detail

    def get(self):
        data = json.load(open(self.filename))
        return data
