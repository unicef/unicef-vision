from django.test import SimpleTestCase

from unicef_vision.models import VisionSyncLog


class TestStrUnicode(SimpleTestCase):
    """Ensure calling str() on model instances returns the right text."""

    def test_vision_sync_log(self):
        instance = VisionSyncLog()
        self.assertTrue(str(instance).startswith(u''))
