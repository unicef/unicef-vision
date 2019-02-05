from django.contrib import admin

from unicef_vision.admin import VisionLoggerAdmin

from .models import VisionLog

admin.site.register(VisionLog, VisionLoggerAdmin)
