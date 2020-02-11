import argparse
import json
import logging
import os
from urllib.parse import urljoin

import requests
from django.conf import settings
from requests.auth import HTTPDigestAuth

from unicef_vision.settings import TIMEOUT

logger = logging.getLogger(__name__)


class VisionAPIClient:
    """Client to Synchronize with Vision"""

    def __init__(self, username=None, password=None, base_url=settings.VISION_URL):
        self.base_url = base_url
        if username and password:
            self.auth = HTTPDigestAuth(username, password)

    def build_path(self, path=None):
        """ Builds the full path to the service.
        Args:
            path (string): The part of the path you want to append to the base url.
        Returns:
            A string containing the full path to the endpoint.
            e.g if the base_url was "http://woo.com" and the path was
            "databases" it would return "http://woo.com/databases/"
        """
        if path is None:
            return self.base_url
        return urljoin(
            self.base_url, os.path.normpath(path),
        )

    def make_request(self, path):

        response = requests.get(
            self.build_path(path),
            auth=getattr(self, 'auth', ()),
            timeout=TIMEOUT
        )
        return response

    def call_command(self, command_type, **properties):

        payload = json.dumps(
            {
                'type': command_type,
                'command': {
                    'properties': properties
                }
            }
        )

        response = requests.post(
            self.build_path('command'),
            headers={'cache-control': 'application/json'},
            auth=getattr(self, 'auth', ()),
            data=payload,
            timeout=TIMEOUT
        )
        return response


def main():
    """Main method for command line usage"""
    parser = argparse.ArgumentParser(description='VISION API Python Client')

    parser.add_argument('-U', '--username',
                        type=str,
                        default='',
                        help='Optional username for authentication')
    parser.add_argument('-P', '--password',
                        type=str,
                        default='',
                        help='Optional password for authentication')

    args = parser.parse_args()
    VisionAPIClient(username=args.username, password=args.password)


if __name__ == '__main__':  # pragma: no cover
    main()
