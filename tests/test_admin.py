from django.contrib.admin.sites import AdminSite
from django.test import SimpleTestCase

from unicef_vision import admin
from unicef_vision.vision.models import VisionLog


class TestVisionAdmin(SimpleTestCase):
    def setUp(self):
        self.admin = admin.VisionLoggerAdmin(VisionLog, AdminSite())
        self.request = MockRequest()

    def test_has_add_permission(self):
        self.assertFalse(self.admin.has_add_permission(self.request))


class MockRequest:
    pass
