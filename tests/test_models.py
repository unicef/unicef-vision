from django.test import SimpleTestCase

from unicef_vision.vision.models import VisionLog


class TestStrUnicode(SimpleTestCase):
    """Ensure calling str() on model instances returns the right text."""

    def test_vision_sync_log(self):
        instance = VisionLog()
        self.assertTrue(str(instance).startswith(u''))
