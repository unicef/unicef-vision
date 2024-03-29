import datetime
import logging
import sys
import types
from abc import ABCMeta, abstractmethod
from collections import OrderedDict

from django.db.models import NOT_PROVIDED
from django.utils.encoding import force_str

from unicef_vision.exceptions import VisionException
from unicef_vision.loaders import FileDataLoader, VisionDataLoader
from unicef_vision.settings import INSIGHT_DATE_FORMAT
from unicef_vision.utils import get_vision_logger_domain_model

logger = logging.getLogger(__name__)


class Empty:
    pass


class DataSynchronizer:
    __metaclass__ = ABCMeta

    REQUIRED_KEYS = {}
    GLOBAL_CALL = False
    LOADER_CLASS = None
    LOADER_EXTRA_KWARGS = []
    detail = None
    business_area_code = None

    @abstractmethod
    def _convert_records(self, records):  # pragma: no cover
        pass

    @abstractmethod
    def _save_records(self, records):  # pragma: no cover
        pass

    def set_kwargs(self, **kwargs):
        return {key: value for key, value in kwargs.items()}

    def __init__(self, detail=None, business_area_code=None, *args, **kwargs) -> None:
        self.detail = detail
        self.business_area_code = business_area_code
        logger.info("Synchronizer is {} - {} {}".format(self.__class__.__name__, self.detail, self.business_area_code))
        self.kwargs = self.set_kwargs(**kwargs)

    def _filter_records(self, records):
        def is_valid_record(record):
            for key in self.REQUIRED_KEYS:
                if key not in record:
                    return False
            return True

        return [rec for rec in records if is_valid_record(rec)]

    def preload(self):  # pragma: no cover
        """hook to execute custom code before loading"""
        pass

    def logger_parameters(self):
        return {
            "handler_name": self.__class__.__name__,
            "business_area_code": self.business_area_code,
        }

    def sync(self):
        """
        Performs the database sync
        :return:
        """
        self.log = get_vision_logger_domain_model()(**self.logger_parameters())

        data_getter = self.LOADER_CLASS(**self.kwargs)

        try:
            original_records = data_getter.get()
            logger.info("{} records returned from get".format(len(original_records)))

            converted_records = self._convert_records(original_records)
            self.log.total_records = len(converted_records)
            logger.info("{} records returned from conversion".format(len(converted_records)))

            totals = self._save_records(converted_records)
        except Exception as e:
            logger.info("sync", exc_info=True)
            self.log.exception_message = force_str(e)
            traceback = sys.exc_info()[2]
            raise VisionException(force_str(e)).with_traceback(traceback)
        else:
            if isinstance(totals, dict):
                self.log.total_processed = totals.get("processed", 0)
                self.log.details = totals.get("details", "")
                self.log.total_records = totals.get("total_records", self.log.total_records)
            else:
                self.log.total_processed = totals
            self.log.successful = True
        finally:
            self.log.save()


class VisionDataSynchronizer(DataSynchronizer):
    __metaclass__ = ABCMeta

    ENDPOINT = None
    LOADER_CLASS = VisionDataLoader

    def __init__(self, detail=None, business_area_code=None, *args, **kwargs) -> None:
        if business_area_code is None and not self.GLOBAL_CALL:
            raise VisionException("business_area_code is required")
        if self.ENDPOINT is None:
            raise VisionException("You must set the ENDPOINT name")
        super().__init__(detail, business_area_code, *args, **kwargs)

    def _convert_records(self, records):
        if isinstance(records, list):
            return records
        elif records and "ROWSET" in records:
            records = records["ROWSET"]["ROW"]
            if isinstance(records, list):
                return records
            else:
                return [
                    records,
                ]
        return []

    def set_kwargs(self, **kwargs):
        kwargs = super().set_kwargs(**kwargs)
        kwargs["endpoint"] = self.ENDPOINT
        if self.detail:
            kwargs["detail"] = self.detail
        if self.business_area_code:
            kwargs["businessarea"] = self.business_area_code
        return kwargs


class FileDataSynchronizer(DataSynchronizer):
    __metaclass__ = ABCMeta

    LOADER_CLASS = FileDataLoader

    def __init__(self, business_area_code=None, *args, **kwargs):
        filename = kwargs.get("filename", None)
        if not filename:
            raise VisionException("You need provide the path to the file")
        self.filename = filename
        super().__init__(business_area_code, *args, **kwargs)

    def set_kwargs(self, **kwargs):
        kwargs = super().set_kwargs(**kwargs)
        kwargs["filename"] = self.filename
        return kwargs


class MultiModelDataSynchronizer(VisionDataSynchronizer):
    MODEL_MAPPING = {}
    MAPPING = OrderedDict()
    DATE_FIELDS = []
    DEFAULTS = {}
    FIELD_HANDLERS = {}

    def _get_field_value(self, field_name, field_json_code, json_item, model):
        if field_json_code in self.DATE_FIELDS:
            # parsing field as date
            return datetime.datetime.strptime(json_item[field_json_code], INSIGHT_DATE_FORMAT).date()
        elif field_name in self.MODEL_MAPPING.keys():
            # this is related model, so we need to fetch somehow related object.
            related_model = self.MODEL_MAPPING[field_name]

            if isinstance(related_model, types.FunctionType):
                # callable provided, object should be returned from it
                result = related_model(data=json_item, key_field=field_json_code)
            else:
                # model class provided, related object can be fetched with query by field
                # analogue of field_json_code
                reversed_dict = dict(
                    zip(
                        self.MAPPING[field_name].values(),
                        self.MAPPING[field_name].keys(),
                    )
                )
                result = related_model.objects.get(
                    **{reversed_dict[field_json_code]: json_item.get(field_json_code, None)}
                )
        else:
            # field can be used as it is without custom mappings. if field has default, it should be used
            result = json_item.get(field_json_code, Empty)
            if result is Empty:
                # try to get default for field
                field_default = model._meta.get_field(field_name).default
                if field_default is not NOT_PROVIDED:
                    result = field_default

        # additional logic on field may be applied
        value_handler = self.FIELD_HANDLERS.get({y: x for x, y in self.MODEL_MAPPING.items()}.get(model), {}).get(
            field_name, None
        )
        if value_handler:
            result = value_handler(result)
        return result

    def _process_record(self, json_item):
        try:
            for model_name, model in self.MODEL_MAPPING.items():
                mapped_item = dict(
                    [
                        (
                            field_name,
                            self._get_field_value(field_name, field_json_code, json_item, model),
                        )
                        for field_name, field_json_code in self.MAPPING[model_name].items()
                    ]
                )
                kwargs = dict(
                    [
                        (field_name, value)
                        for field_name, value in mapped_item.items()
                        if model._meta.get_field(field_name).unique
                    ]
                )

                if not kwargs:
                    for fields in model._meta.unique_together:
                        if all(field in mapped_item.keys() for field in fields):
                            unique_fields = fields
                            break

                    kwargs = {field: mapped_item[field] for field in unique_fields}

                defaults = dict(
                    [
                        (field_name, value)
                        for field_name, value in mapped_item.items()
                        if field_name not in kwargs.keys()
                    ]
                )
                defaults.update(self.DEFAULTS.get(model, {}))
                model.objects.update_or_create(defaults=defaults, **kwargs)
        except Exception:
            logger.warning("Exception processing record", exc_info=True)

    def _save_records(self, records):
        processed = 0
        filtered_records = self._filter_records(records)

        for record in filtered_records:
            self._process_record(record)
            processed += 1
        return processed
