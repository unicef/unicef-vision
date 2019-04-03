from django.db import models
from django.utils.translation import ugettext_lazy as _


class AbstractVisionLog(models.Model):
    """Represents a sync log for Vision SAP"""

    handler_name = models.CharField(max_length=50, verbose_name=_('Handler Name'))
    business_area_code = models.CharField(max_length=10, verbose_name=_('Business Area Code'), null=True, blank=True)
    total_records = models.IntegerField(default=0, verbose_name=_('Total Records'))
    total_processed = models.IntegerField(default=0, verbose_name=_('Total Processed'))
    successful = models.BooleanField(default=False, verbose_name=_('Successful'))
    details = models.CharField(max_length=2048, blank=True, default='', verbose_name=_('Details'))
    exception_message = models.TextField(blank=True, default='', verbose_name=_('Exception Message'))
    date_processed = models.DateTimeField(auto_now=True, verbose_name=_('Date Processed'))

    def __str__(self):
        return u'{0.business_area_code}: {0.date_processed}:{0.successful} {0.total_processed}'.format(self)

    class Meta:
        abstract = True
