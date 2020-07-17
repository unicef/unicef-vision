import json
import os

import mock
from django.conf import settings
from django.test import override_settings, TestCase

from unicef_vision.exceptions import VisionException
from unicef_vision.loaders import FileDataLoader, INSIGHT_NO_DATA_MESSAGE, VisionDataLoader
from unicef_vision.utils import base_headers

FAUX_INSIGHT_URL = 'https://api.example.com/foo.svc/'


class TestVisionDataLoader(TestCase):
    """Exercise VisionDataLoader class"""
    # Note - I don't understand why, but @override_settings(INSIGHT_URL=FAUX_INSIGHT_URL) doesn't work when I apply
    # it at the TestCase class level instead of each individual test case.

    def _assertGetFundamentals(self, url, mock_requests, mock_get_response):
        """Assert common things about the call to loader.get()"""
        # Ensure requests.get() was called as expected
        self.assertEqual(mock_requests.get.call_count, 1)
        self.assertEqual(mock_requests.get.call_args[0], (url, ))
        self.assertEqual(mock_requests.get.call_args[1], {
            'headers': base_headers,
            'timeout': 400
        })
        # Ensure response.json() was called as expected
        self.assertEqual(mock_get_response.json.call_count, 1)
        self.assertEqual(mock_get_response.json.call_args[0], tuple())
        self.assertEqual(mock_get_response.json.call_args[1], {})

    def test_instantiation_no_business_area_code(self):
        """Ensure I can create a loader without specifying a business_area_code"""
        loader = VisionDataLoader('GetSomeStuff_JSON')
        self.assertEqual(loader.url, '{}/GetSomeStuff_JSON'.format(loader.URL))

    def test_instantiation_with_business_area_code(self):
        """Ensure I can create a loader that specifies a business_area_code"""
        test_business_area_code = 'ABC'
        loader = VisionDataLoader('GetSomeStuff_JSON', businessarea=test_business_area_code)
        self.assertEqual(loader.url, '{}/GetSomeStuff_JSON/?businessarea=ABC'.format(loader.URL))

    def test_instantiation_url_construction(self):
        """Ensure loader URL is constructed correctly regardless of whether or not base URL ends with a slash"""
        loader = VisionDataLoader('GetSomeStuff_JSON')
        self.assertEqual(loader.url, '{}/GetSomeStuff_JSON'.format(loader.URL))

    @override_settings(INSIGHT_URL=FAUX_INSIGHT_URL)
    @mock.patch('unicef_vision.loaders.requests', spec=['get'])
    def test_get_success_with_response(self, mock_requests):
        """Test loader.get() when the response is 200 OK and data is returned"""
        mock_get_response = mock.Mock(spec=['status_code', 'json'])
        mock_get_response.status_code = 200
        mock_get_response.json = mock.Mock(return_value=[42])
        mock_requests.get = mock.Mock(return_value=mock_get_response)

        loader = VisionDataLoader('GetSomeStuff_JSON')
        response = loader.get()

        self._assertGetFundamentals(loader.url, mock_requests, mock_get_response)

        self.assertEqual(response, [42])

    @override_settings(INSIGHT_URL=FAUX_INSIGHT_URL)
    @mock.patch('unicef_vision.loaders.requests', spec=['get'])
    def test_get_success_with_response_and_headers(self, mock_requests):
        """Test loader.get() when the response is 200 OK and data is returned"""
        mock_get_response = mock.Mock(spec=['status_code', 'json'])
        mock_get_response.status_code = 200
        mock_get_response.json = mock.Mock(return_value=[42])
        mock_requests.get = mock.Mock(return_value=mock_get_response)

        loader = VisionDataLoader('GetSomeStuff_JSON', headers=(('Test', 'Header'), ))

        response = loader.get()

        self.assertEqual(mock_requests.get.call_count, 1)
        self.assertEqual(mock_requests.get.call_args[0], (loader.url, ))
        headers = base_headers.copy()
        headers['Test'] = 'Header'
        self.assertEqual(mock_requests.get.call_args[1], {'headers': headers,
                                                          'timeout': 400})
        self.assertEqual(response, [42])

    @override_settings(INSIGHT_URL=FAUX_INSIGHT_URL)
    @mock.patch('unicef_vision.loaders.requests', spec=['get'])
    def test_get_success_no_response(self, mock_requests):
        """Test loader.get() when the response is 200 OK but no data is returned"""
        mock_get_response = mock.Mock(spec=['status_code', 'json'])
        mock_get_response.status_code = 200
        mock_get_response.json = mock.Mock(return_value=INSIGHT_NO_DATA_MESSAGE)
        mock_requests.get = mock.Mock(return_value=mock_get_response)

        loader = VisionDataLoader('GetSomeStuff_JSON')
        response = loader.get()

        self._assertGetFundamentals(loader.url, mock_requests, mock_get_response)

        self.assertEqual(response, [])

    @override_settings(INSIGHT_URL=FAUX_INSIGHT_URL)
    @mock.patch('unicef_vision.loaders.requests', spec=['get'])
    def test_get_failure(self, mock_requests):
        """Test loader.get() when the response is something other than 200"""
        # Note that in contrast to the other mock_get_response variables declared in this test case, this one
        # doesn't have 'json' in the spec. I don't expect the loaderto access response.json during this test, so if
        # it does this configuration ensures the test will fail.
        mock_get_response = mock.Mock(spec=['status_code'])
        mock_get_response.status_code = 401
        mock_requests.get = mock.Mock(return_value=mock_get_response)

        loader = VisionDataLoader('GetSomeStuff_JSON')
        with self.assertRaises(VisionException) as context_manager:
            loader.get()

        # Assert that the status code is repeated in the message of the raised exception.
        self.assertIn('401', str(context_manager.exception))

        # Ensure get was called as normal.
        self.assertEqual(mock_requests.get.call_count, 1)
        self.assertEqual(mock_requests.get.call_args[0], (loader.url, ))
        self.assertEqual(mock_requests.get.call_args[1], {
            'headers': base_headers,
            'timeout': 400
        })

    def test_detail(self):
        a = VisionDataLoader("api", "123")
        self.assertEqual(a.url, "{}/api/123".format(settings.INSIGHT_URL))


class TestFileDataLoader(TestCase):
    def setUp(self):
        self.test_file_content = 'abcd'
        self.filename = 'tests/test.json'
        with open(self.filename, 'w') as f:
            json.dump(self.test_file_content, f)

        self.addCleanup(os.remove, self.filename)

    def test_init(self):
        fl = FileDataLoader(self.filename)
        self.assertEqual(fl.filename, self.filename)

    def test_get(self):
        fl = FileDataLoader(self.filename)
        self.assertEqual(fl.get(), self.test_file_content)
