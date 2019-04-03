import json
import logging

import requests
from django.conf import settings

from unicef_vision.exceptions import VisionException

logger = logging.getLogger(__name__)

# VISION_NO_DATA_MESSAGE is what the remote vision system returns when it has no data
VISION_NO_DATA_MESSAGE = 'No Data Available'


class VisionDataLoader:
    """Base class for Data Loading"""
    URL = settings.VISION_URL

    def __init__(self, business_area_code=None, endpoint=None):
        if endpoint is None:
            raise VisionException('You must set the ENDPOINT name')

        separator = '' if self.URL.endswith('/') else '/'

        self.url = '{}{}{}'.format(self.URL, separator, endpoint)
        if business_area_code:
            self.url += '/{}'.format(business_area_code)

        logger.info('About to get data from {}'.format(self.url))

    def get(self):
        response = requests.get(
            self.url,
            headers={'Content-Type': 'application/json'},
            auth=(settings.VISION_USER, settings.VISION_PASSWORD),
            verify=False
        )

        if response.status_code != 200:
            raise VisionException('Load data failed! Http code: {}'.format(response.status_code))
        json_response = response.json()
        if json_response == VISION_NO_DATA_MESSAGE:
            return []

        return json_response


class ManualDataLoader(VisionDataLoader):
    """
    Can be used to sync single objects from VISION url templates:
    /endpoint if no business_area_code or object_number
    /endpoint/business_area_code if no object number provided
    /endpoint/object_number else
    """

    def __init__(self, business_area_code=None, endpoint=None, object_number=None):
        if not object_number:
            super().__init__(business_area_code=business_area_code, endpoint=endpoint)
        else:
            if endpoint is None:
                raise VisionException('You must set the ENDPOINT name')
            self.url = '{}/{}/{}'.format(
                self.URL,
                endpoint,
                object_number
            )


class FileDataLoader:
    """Loader to read json file instead of REST API"""

    def __init__(self, filename):
        self.filename = filename

    def get(self):
        data = json.load(open(self.filename))
        return data
