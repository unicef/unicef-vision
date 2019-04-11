import datetime
import json

from django.test import override_settings, SimpleTestCase

from unittest import mock

from unicef_vision import utils
from unicef_vision.loaders import VISION_NO_DATA_MESSAGE

FAUX_VISION_URL = 'https://api.example.com/foo.svc/'
FAUX_VISION_USER = 'jane_user'
FAUX_VISION_PASSWORD = 'password123'


@override_settings(VISION_URL=FAUX_VISION_URL)
@override_settings(VISION_USER=FAUX_VISION_USER)
@override_settings(VISION_PASSWORD=FAUX_VISION_PASSWORD)
class TestGetDataFromInsight(SimpleTestCase):
    @mock.patch('unicef_vision.utils.requests.get')
    def test_status_http_error(self, mock_requests):
        mock_response = mock.Mock()
        mock_response.status_code = 404

        mock_requests.return_value = mock_response
        status, reason = utils.get_data_from_insight('GetSomeStuff_JSON')

        self.assertFalse(status)
        self.assertEqual(reason, 'Loading data from Vision Failed, status {}'.format(mock_response.status_code))

    @mock.patch('unicef_vision.utils.requests.get')
    def test_invalid_request(self, mock_requests):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json = mock.Mock(return_value=VISION_NO_DATA_MESSAGE)

        data = {}
        mock_requests.return_value = mock_response
        status, reason = utils.get_data_from_insight('GetSomeStuff_JSON', data)
        self.assertFalse(status)
        self.assertEqual(
            reason,
            'Loading data from Vision Failed, no valid response returned for data: {}'.format(data)
        )

    @mock.patch('unicef_vision.utils.requests.get')
    def test_status_http_ok(self, mock_requests):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        res = '{"v": 1}'
        mock_response.json = mock.Mock(return_value=res)

        mock_requests.return_value = mock_response
        status, response = utils.get_data_from_insight('GetSomeStuff_JSON')

        self.assertTrue(status)
        self.assertEqual(response, json.loads(res))


class TestWCFJSONDateAsDatetime(SimpleTestCase):
    def test_none(self):
        self.assertIsNone(utils.wcf_json_date_as_datetime(None))

    def test_datetime(self):
        date = "/Date(1361336400000)/"
        result = utils.wcf_json_date_as_datetime(date)
        self.assertEqual(result, datetime.datetime(2013, 2, 20, 5, 0))

    def test_datetime_positive_sign(self):
        date = "/Date(00000001+1000)/"
        result = utils.wcf_json_date_as_datetime(date)
        self.assertEqual(
            result,
            datetime.datetime(1970, 1, 1, 10, 0, 0, 1000)
        )

    def test_datetime_negative_sign(self):
        date = "/Date(00000001-1000)/"
        result = utils.wcf_json_date_as_datetime(date)
        self.assertEqual(
            result,
            datetime.datetime(1969, 12, 31, 14, 0, 0, 1000)
        )


class TestWCFJSONDateAsDate(SimpleTestCase):
    def test_none(self):
        self.assertIsNone(utils.wcf_json_date_as_date(None))

    def test_datetime(self):
        date = "/Date(1361336400000)/"
        result = utils.wcf_json_date_as_date(date)
        self.assertEqual(result, datetime.date(2013, 2, 20))

    def test_datetime_positive_sign(self):
        date = "/Date(00000001+1000)/"
        result = utils.wcf_json_date_as_date(date)
        self.assertEqual(
            result,
            datetime.date(1970, 1, 1)
        )

    def test_datetime_negative_sign(self):
        date = "/Date(00000001-1000)/"
        result = utils.wcf_json_date_as_date(date)
        self.assertEqual(
            result,
            datetime.date(1969, 12, 31)
        )


class TestCompDecimals(SimpleTestCase):
    def test_not_equal(self):
        self.assertFalse(utils.comp_decimals(0.2, 0.3))

    def test_equal(self):
        self.assertTrue(utils.comp_decimals(0.2, 0.2))
