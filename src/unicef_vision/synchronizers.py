import json
import logging
import sys
import types
from abc import ABCMeta, abstractmethod
from collections import OrderedDict

from django.db.models import NOT_PROVIDED
from django.utils.encoding import force_text

from unicef_vision.exceptions import VisionException
from unicef_vision.loaders import FileDataLoader, ManualDataLoader, VisionDataLoader
from unicef_vision.models import VisionLog
from unicef_vision.utils import wcf_json_date_as_datetime

logger = logging.getLogger(__name__)


class Empty(object):
    pass


class DataSynchronizer(object):

    __metaclass__ = ABCMeta

    REQUIRED_KEYS = {}
    GLOBAL_CALL = False
    LOADER_CLASS = None
    LOGGER_CLASS = VisionLog
    LOADER_EXTRA_KWARGS = []
    country = None

    @abstractmethod
    def _convert_records(self, records):
        pass

    @abstractmethod
    def _save_records(self, records):
        pass

    @abstractmethod
    def _get_kwargs(self):
        return {}

    def _filter_records(self, records):
        def is_valid_record(record):
            for key in self.REQUIRED_KEYS:
                if key not in record:
                    return False
            return True

        return [rec for rec in records if is_valid_record(rec)]

    def preload(self):
        """hook to execute custom code before loading"""
        pass

    def set_logger(self):
        self.log = self.LOGGER_CLASS(
            handler_name=self.__class__.__name__
        )

    def sync(self):
        """
        Performs the database sync
        :return:
        """
        self.set_logger()

        loader_kwargs = self._get_kwargs()
        loader_kwargs.update({
            kwarg_name: getattr(self, kwarg_name)
            for kwarg_name in self.LOADER_EXTRA_KWARGS
        })
        data_getter = self.LOADER_CLASS(**loader_kwargs)

        try:
            original_records = data_getter.get()
            logger.info('{} records returned from get'.format(len(original_records)))

            converted_records = self._convert_records(original_records)
            self.log.total_records = len(converted_records)
            logger.info('{} records returned from conversion'.format(len(converted_records)))

            totals = self._save_records(converted_records)
        except Exception as e:
            logger.info('sync', exc_info=True)
            self.log.exception_message = force_text(e)
            traceback = sys.exc_info()[2]
            raise VisionException(force_text(e)).with_traceback(traceback)
        else:
            if isinstance(totals, dict):
                self.log.total_processed = totals.get('processed', 0)
                self.log.details = totals.get('details', '')
                self.log.total_records = totals.get('total_records', self.log.total_records)
            else:
                self.log.total_processed = totals
            self.log.successful = True
        finally:
            self.log.save()


class VisionDataSynchronizer(DataSynchronizer):
    __metaclass__ = ABCMeta

    ENDPOINT = None
    LOADER_CLASS = VisionDataLoader

    def __init__(self, country=None):
        if not country:
            raise VisionException('Country is required')
        if self.ENDPOINT is None:
            raise VisionException('You must set the ENDPOINT name')

        logger.info('Synchronizer is {}'.format(self.__class__.__name__))

        self.country = country

        logger.info('Country is {}'.format(country))

    def _get_kwargs(self):
        return {
            'country': self.country,
            'endpoint': self.ENDPOINT,
        }


class FileDataSynchronizer(DataSynchronizer):
    __metaclass__ = ABCMeta

    LOADER_CLASS = FileDataLoader
    LOADER_EXTRA_KWARGS = ['filename', ]

    def __init__(self, country=None, *args, **kwargs):

        filename = kwargs.get('filename', None)
        if not country:
            raise VisionException('Country is required')
        if not filename:
            raise VisionException('You need provide the path to the file')

        logger.info('Synchronizer is {}'.format(self.__class__.__name__))

        self.filename = filename
        self.country = country
        logger.info('Country is {}'.format(country))

        super().__init__(country, *args, **kwargs)


class MultiModelDataSynchronizer(VisionDataSynchronizer):
    MODEL_MAPPING = {}
    MAPPING = OrderedDict()
    DATE_FIELDS = []
    DEFAULTS = {}
    FIELD_HANDLERS = {}

    def _convert_records(self, records):
        if isinstance(records, list):
            return records
        try:
            return json.loads(records)
        except ValueError:
            return []

    def _get_field_value(self, field_name, field_json_code, json_item, model):
        if field_json_code in self.DATE_FIELDS:
            # parsing field as date
            return wcf_json_date_as_datetime(json_item[field_json_code])
        elif field_name in self.MODEL_MAPPING.keys():
            # this is related model, so we need to fetch somehow related object.
            related_model = self.MODEL_MAPPING[field_name]

            if isinstance(related_model, types.FunctionType):
                # callable provided, object should be returned from it
                result = related_model(data=json_item, key_field=field_json_code)
            else:
                # model class provided, related object can be fetched with query by field
                # analogue of field_json_code
                reversed_dict = dict(zip(
                    self.MAPPING[field_name].values(),
                    self.MAPPING[field_name].keys()
                ))
                result = related_model.objects.get(**{
                    reversed_dict[field_json_code]: json_item.get(field_json_code, None)
                })
        else:
            # field can be used as it is without custom mappings. if field has default, it should be used
            result = json_item.get(field_json_code, Empty)
            if result is Empty:
                # try to get default for field
                field_default = model._meta.get_field(field_name).default
                if field_default is not NOT_PROVIDED:
                    result = field_default

        # additional logic on field may be applied
        value_handler = self.FIELD_HANDLERS.get(
            {y: x for x, y in self.MODEL_MAPPING.items()}.get(model), {}
        ).get(field_name, None)
        if value_handler:
            result = value_handler(result)
        return result

    def _process_record(self, json_item):
        try:
            for model_name, model in self.MODEL_MAPPING.items():
                mapped_item = dict(
                    [(field_name, self._get_field_value(field_name, field_json_code, json_item, model))
                     for field_name, field_json_code in self.MAPPING[model_name].items()]
                )
                kwargs = dict(
                    [(field_name, value) for field_name, value in mapped_item.items()
                     if model._meta.get_field(field_name).unique]
                )

                if not kwargs:
                    for fields in model._meta.unique_together:
                        if all(field in mapped_item.keys() for field in fields):
                            unique_fields = fields
                            break

                    kwargs = {
                        field: mapped_item[field] for field in unique_fields
                    }

                defaults = dict(
                    [(field_name, value) for field_name, value in mapped_item.items()
                     if field_name not in kwargs.keys()]
                )
                defaults.update(self.DEFAULTS.get(model, {}))
                model.objects.update_or_create(
                    defaults=defaults, **kwargs
                )
        except Exception:
            logger.warning('Exception processing record', exc_info=True)

    def _save_records(self, records):
        processed = 0
        filtered_records = self._filter_records(records)

        for record in filtered_records:
            self._process_record(record)
            processed += 1
        return processed


class ManualVisionSynchronizer(MultiModelDataSynchronizer):
    LOADER_CLASS = ManualDataLoader
    LOADER_EXTRA_KWARGS = ['object_number', ]

    def __init__(self, country=None, object_number=None):
        self.object_number = object_number

        if not object_number:
            super().__init__(country=country)
        else:
            if self.ENDPOINT is None:
                raise VisionException('You must set the ENDPOINT name')

            self.country = country

            logger.info('Country is {}'.format(country))
