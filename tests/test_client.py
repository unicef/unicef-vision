import sys

import responses
from django.test import SimpleTestCase

from unicef_vision import client
from unicef_vision.client import main


class TestVisionClient(SimpleTestCase):
    def setUp(self):
        self.client = client.VisionAPIClient()

    def test_init(self):
        c = client.VisionAPIClient()
        self.assertTrue(c.base_url)

    def test_init_auth(self):
        """Check that auth attribute if username and password provided"""
        c = client.VisionAPIClient(username="test", password="123")
        self.assertTrue(c.base_url)
        self.assertIsInstance(c.auth, client.HTTPDigestAuth)

    def test_build_path_none(self):
        """If no path provided, use base_url attribute"""
        path = self.client.build_path()
        self.assertEqual(path, self.client.base_url)

    def test_build_path(self):
        path = self.client.build_path("api")
        self.assertEqual(path, "{}/api".format(self.client.base_url))

    @responses.activate
    def test_make_request(self):
        c = client.VisionAPIClient(username="test", password="123")
        path = ''
        responses.add(
            responses.GET, 'https://api.example.com', status=200,
            json={},
        )
        c.make_request(path)

    @responses.activate
    def test_call_command(self):
        c = client.VisionAPIClient(username="test", password="123")
        command_type = ''
        responses.add(
            responses.POST, 'https://api.example.com/command', status=200,
            json={},
        )
        c.call_command(command_type)

    def test_main(self):
        sys.argv[1:] = ['-U', 'username', '-P', 'password']
        main()
