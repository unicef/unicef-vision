import json

import requests
from celery.utils.log import get_task_logger
from django.conf import settings

from unicef_vision.exceptions import VisionException

logger = get_task_logger('vision.synchronize')

# VISION_NO_DATA_MESSAGE is what the remote vision system returns when it has no data
VISION_NO_DATA_MESSAGE = 'No Data Available'


class VisionDataLoader(object):
    URL = settings.VISION_URL

    def __init__(self, country=None, endpoint=None):
        if endpoint is None:
            raise VisionException('You must set the ENDPOINT name')

        separator = '' if self.URL.endswith('/') else '/'

        self.url = '{}{}{}'.format(self.URL, separator, endpoint)
        if country:
            self.url += '/{}'.format(country)

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
    /endpoint if no country or object_number
    /endpoint/country if no object number provided
    /endpoint/object_number else
    """

    def __init__(self, country=None, endpoint=None, object_number=None):
        if not object_number:
            super().__init__(country=country, endpoint=endpoint)
        else:
            if endpoint is None:
                raise VisionException('You must set the ENDPOINT name')
            self.url = '{}/{}/{}'.format(
                self.URL,
                endpoint,
                object_number
            )


class FileDataLoader(object):

    def __init__(self, filename):
        self.filename = filename

    def get(self):
        data = json.load(open(self.filename))
        return data
