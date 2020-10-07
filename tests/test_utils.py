from django.test import override_settings, SimpleTestCase

import mock

from unicef_vision import utils
from unicef_vision.loaders import INSIGHT_NO_DATA_MESSAGE

FAUX_INSIGHT_URL = 'https://api.example.com/foo.svc/'


@override_settings(INSIGHT_URL=FAUX_INSIGHT_URL)
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
        mock_response.json = mock.Mock(return_value=INSIGHT_NO_DATA_MESSAGE)

        data = {}
        mock_requests.return_value = mock_response
        status, reason = utils.get_data_from_insight('GetSomeStuff_JSON', data)
        self.assertTrue(status)
        self.assertEqual(
            reason, INSIGHT_NO_DATA_MESSAGE
            # 'Loading data from Vision Failed, no valid response returned for data: {}'.format(data)
        )

    @mock.patch('unicef_vision.utils.requests.get')
    def test_status_http_ok(self, mock_requests):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        res = {"v": 1}
        mock_response.json = mock.Mock(return_value=res)

        mock_requests.return_value = mock_response
        status, response = utils.get_data_from_insight('GetSomeStuff_JSON')

        self.assertTrue(status)
        self.assertEqual(response, res)


class TestCompDecimals(SimpleTestCase):
    def test_not_equal(self):
        self.assertFalse(utils.comp_decimals(0.2, 0.3))

    def test_equal(self):
        self.assertTrue(utils.comp_decimals(0.2, 0.2))
