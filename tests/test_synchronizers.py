import copy
import json
import mock
import os
import types

from datetime import datetime
from collections import OrderedDict
from django.db.models import NOT_PROVIDED
from django.conf import settings
from django.test import override_settings, TestCase
from django.utils.timezone import now as django_now

from unicef_vision.exceptions import VisionException
from unicef_vision.synchronizers import (
    VisionDataSynchronizer,
    FileDataSynchronizer,
    MultiModelDataSynchronizer,
    ManualVisionSynchronizer
)
from unicef_vision.vision.models import VisionLog

FAUX_VISION_URL = 'https://api.example.com/foo.svc/'
FAUX_VISION_USER = 'jane_user'
FAUX_VISION_PASSWORD = 'password123'


class _MySynchronizer(VisionDataSynchronizer):
    """Bare bones synchronizer class. Exists because VisionDataSynchronizer is abstract; this is concrete but
    """
    ENDPOINT = 'GetSomeStuff_JSON'

    def _convert_records(self, records):
        pass

    def _save_records(self, records):
        pass


class TestVisionDataSynchronizerInit(TestCase):
    """Exercise initialization of VisionDataSynchronizer class"""

    def setUp(self):
        self.synchronizer_class = _MySynchronizer

    def test_instantiation_no_business_area_code(self):
        """Ensure I can't create a synchronizer without specifying a business_area_code"""
        with self.assertRaises(VisionException) as context_manager:
            self.synchronizer_class()

        self.assertEqual('business_area_code is required', str(context_manager.exception))

    def test_instantiation_no_endpoint(self):
        """Ensure I can't create a synchronizer without specifying an endpoint"""
        class _MyBadSynchronizer(self.synchronizer_class):
            """Synchronizer class that doesn't set self.ENDPOINT"""
            ENDPOINT = None

        test_business_area_code = 'ABC'

        with self.assertRaises(VisionException) as context_manager:
            _MyBadSynchronizer(business_area_code=test_business_area_code)

        self.assertEqual('You must set the ENDPOINT name', str(context_manager.exception))

    @mock.patch('unicef_vision.synchronizers.logger.info')
    def test_instantiation_positive(self, mock_logger_info):
        """Exercise successfully creating a synchronizer"""
        test_business_area_code = 'ABC'

        self.synchronizer_class(business_area_code=test_business_area_code)

        # Ensure msgs are logged
        self.assertEqual(mock_logger_info.call_count, 2)
        expected_msg = 'Synchronizer is _MySynchronizer'
        self.assertEqual(mock_logger_info.call_args_list[0][0], (expected_msg, ))
        self.assertEqual(mock_logger_info.call_args_list[0][1], {})

        expected_msg = 'business_area_code is ' + test_business_area_code
        self.assertEqual(mock_logger_info.call_args_list[1][0], (expected_msg, ))
        self.assertEqual(mock_logger_info.call_args_list[1][1], {})


class TestVisionDataSynchronizerSync(TestCase):
    """Exercise the sync() method of VisionDataSynchronizer class"""

    def _assertVisionLogFundamentals(self, total_records, total_processed, details='', exception_message='',
                                         successful=True):
        """Assert common properties of the VisionLog record that should have been created during a test. Populate
        the method parameters with what you expect to see in the VisionLog record.
        """
        sync_logs = VisionLog.objects.all()

        self.assertEqual(len(sync_logs), 1)

        sync_log = sync_logs[0]

        self.assertEqual(sync_log.handler_name, '_MySynchronizer')
        self.assertEqual(sync_log.total_records, total_records)
        self.assertEqual(sync_log.total_processed, total_processed)
        self.assertEqual(sync_log.successful, successful)
        if details:
            self.assertEqual(sync_log.details, details)
        else:
            self.assertIn(sync_log.details, ('', None))
        if exception_message:
            self.assertEqual(sync_log.exception_message, exception_message)
        else:
            self.assertIn(sync_log.exception_message, ('', None))
        # date_processed is a datetime; there's no way to know the exact microsecond it should contain. As long as
        # it's within a few seconds of now, that's good enough.
        delta = django_now() - sync_log.date_processed
        self.assertLess(delta.seconds, 5)

    def setUp(self):
        self.assertEqual(VisionLog.objects.all().count(), 0)
        self.test_business_area_code = 'ABC'
        self.synchronizer_class = _MySynchronizer

    @mock.patch('unicef_vision.synchronizers.logger.info')
    def test_sync_positive(self, mock_logger_info):
        """Test calling sync() for the mainstream case of success. Tests the following --
            - A VisionLog instance is created and has the expected values
            - # of records returned by vision can differ from the # returned by synchronizer._convert_records()
            - synchronizer._save_records() can return an int (instead of a dict)
            - The int returned by synchronizer._save_records() is recorded properly in the VisionLog record
            - logger.info() is called as expected
            - All calls to synchronizer methods have expected args
        """
        synchronizer = self.synchronizer_class(business_area_code=self.test_business_area_code)

        # These are the dummy records that vision will "return" via mock_loader.get()
        vision_records = [42, 43, 44]
        # These are the dummy records that synchronizer._convert_records() will return. It's intentionally a different
        # length than vision_records to test that these two sets of records are treated differently.
        converted_records = [42, 44]

        mock_loader = mock.Mock()
        mock_loader.url = 'http://example.com'
        mock_loader.get.return_value = vision_records
        MockLoaderClass = mock.Mock(return_value=mock_loader)

        synchronizer.LOADER_CLASS = MockLoaderClass

        mock_convert_records = mock.Mock(return_value=converted_records)
        synchronizer._convert_records = mock_convert_records

        # synchronizer._save_records() should logically return the # of records saved but we're going to make it
        # do something different to ensure that its return value is respected.
        mock_save_records = mock.Mock(return_value=99)
        synchronizer._save_records = mock_save_records

        # Setup is done, now call sync().
        synchronizer.sync()

        self.assertEqual(MockLoaderClass.call_count, 1)
        self.assertEqual(MockLoaderClass.call_args[0], tuple())
        self.assertEqual(MockLoaderClass.call_args[1], {'business_area_code': self.test_business_area_code,
                                                        'endpoint': 'GetSomeStuff_JSON'})

        self.assertEqual(mock_loader.get.call_count, 1)
        self.assertEqual(mock_loader.get.call_args[0], tuple())
        self.assertEqual(mock_loader.get.call_args[1], {})

        self.assertEqual(mock_convert_records.call_count, 1)
        self.assertEqual(mock_convert_records.call_args[0], (vision_records, ))
        self.assertEqual(mock_convert_records.call_args[1], {})

        self.assertEqual(mock_save_records.call_count, 1)
        self.assertEqual(mock_save_records.call_args[0], (converted_records, ))
        self.assertEqual(mock_save_records.call_args[1], {})

        # The first two calls to logger.info()  are part of the instantiation of VisionDataLoader so I don't need to
        # test them here.
        self.assertEqual(mock_logger_info.call_count, 4)
        expected_msg = '{} records returned from get'.format(len(vision_records))
        self.assertEqual(mock_logger_info.call_args_list[2][0], (expected_msg, ))
        self.assertEqual(mock_logger_info.call_args_list[2][1], {})
        expected_msg = '{} records returned from conversion'.format(len(converted_records))
        self.assertEqual(mock_logger_info.call_args_list[3][0], (expected_msg, ))
        self.assertEqual(mock_logger_info.call_args_list[3][1], {})

        self._assertVisionLogFundamentals(len(converted_records), 99)

    def test_sync_save_records_returns_dict(self):
        """Test calling sync() when _save_records() returns a dict. Tests that sync() provides default values
        as necessary and that values in the dict returned by _save_records() are logged.
        """
        synchronizer = self.synchronizer_class(business_area_code=self.test_business_area_code)

        # These are the dummy records that vision will "return" via mock_loader.get()
        records = [42, 43, 44]

        mock_loader = mock.Mock()
        mock_loader.get.return_value = records
        MockLoaderClass = mock.Mock(return_value=mock_loader)

        synchronizer.LOADER_CLASS = MockLoaderClass

        mock_convert_records = mock.Mock(return_value=records)
        synchronizer._convert_records = mock_convert_records

        # I'm going to call sync() twice and test a different value from _save_records() each time.
        # The first dict is empty to prove that sync() behaves properly even when expected values are missing.
        # The second dict contains all expected values, plus an unexpected key/value pair. The extra ensures
        # sync() isn't tripped up by that.
        save_return_values = [{},
                              {'processed': 100,
                               'details': 'Hello world!',
                               'total_records': 200,
                               'foo': 'bar'}
                              ]
        mock_save_records = mock.Mock(side_effect=save_return_values)
        synchronizer._save_records = mock_save_records

        # Setup is done, now call sync().
        synchronizer.sync()

        self._assertVisionLogFundamentals(len(records), 0)

        # Get rid of this log record to simplify the remainder of the test.
        VisionLog.objects.all()[0].delete()

        # Call sync again.
        synchronizer.sync()

        self._assertVisionLogFundamentals(200, 100, details='Hello world!')

    def test_sync_passes_loader_kwargs(self):
        """Test that LOADER_EXTRA_KWARGS on the synchronizer are passed to the loader."""
        class _MyFancySynchronizer(self.synchronizer_class):
            """Synchronizer class that uses LOADER_EXTRA_KWARGS"""
            LOADER_EXTRA_KWARGS = ['FROBNICATE', 'POTRZEBIE']
            FROBNICATE = True
            POTRZEBIE = 2.2

            def _convert_records(self, records):
                return []

            def _save_records(self, records):
                return 0

        synchronizer = _MyFancySynchronizer(business_area_code=self.test_business_area_code)

        mock_loader = mock.Mock()
        mock_loader.get.return_value = [42, 43, 44]
        MockLoaderClass = mock.Mock(return_value=mock_loader)

        synchronizer.LOADER_CLASS = MockLoaderClass

        # Setup is done, now call sync().
        synchronizer.sync()

        self.assertEqual(MockLoaderClass.call_count, 1)
        self.assertEqual(MockLoaderClass.call_args[0], tuple())
        self.assertEqual(MockLoaderClass.call_args[1], {'business_area_code': self.test_business_area_code,
                                                        'endpoint': 'GetSomeStuff_JSON',
                                                        'FROBNICATE': True,
                                                        'POTRZEBIE': 2.2})

    @mock.patch('unicef_vision.synchronizers.logger.info')
    def test_sync_exception_handling(self, mock_logger_info):
        """Test sync() exception handling behavior."""
        synchronizer = self.synchronizer_class(business_area_code=self.test_business_area_code)

        # Force a failure in the attempt to get vision records
        def loader_get_side_effect():
            raise ValueError('Wrong!')

        mock_loader = mock.Mock()
        mock_loader.get.side_effect = loader_get_side_effect
        MockLoaderClass = mock.Mock(return_value=mock_loader)

        synchronizer.LOADER_CLASS = MockLoaderClass

        # _convert_records() and _save_records() should not be called. I mock them so I can verify that.
        mock_convert_records = mock.Mock()
        synchronizer._convert_records = mock_convert_records
        mock_save_records = mock.Mock()
        synchronizer._save_records = mock_save_records

        # Setup is done, now call sync().
        with self.assertRaises(VisionException):
            synchronizer.sync()

        self.assertEqual(mock_convert_records.call_count, 0)
        self.assertEqual(mock_save_records.call_count, 0)

        # The first two calls to logger.info()  are part of the instantiation of VisionDataLoader so I don't need to
        # test them here.
        self.assertEqual(mock_logger_info.call_count, 3)
        expected_msg = 'sync'
        self.assertEqual(mock_logger_info.call_args_list[2][0], (expected_msg, ))
        self.assertEqual(mock_logger_info.call_args_list[2][1], {'exc_info': True})

        self._assertVisionLogFundamentals(0, 0, exception_message='Wrong!', successful=False)


class TestFileDataSynchronizer(TestCase):
    """
    Exercise initialization of FileDataSynchronizer class
    TODO: test sync maybe
    """

    def setUp(self):
        self.synchronizer_class = FileDataSynchronizer
        self.synchronizer_class.ENDPOINT = 'GetSomeStuff_JSON'

    def test_instantiation_no_business_area_code(self):
        """Ensure I can't create a synchronizer without specifying a business_area_code"""
        with self.assertRaises(VisionException) as context_manager:
            self.synchronizer_class()

        self.assertEqual('business_area_code is required', str(context_manager.exception))

    def test_instantiation_no_filename(self):
        """Ensure I can't create a synchronizer without specifying a filename"""
        test_business_area_code = 'ABC'

        with self.assertRaises(VisionException) as context_manager:
            self.synchronizer_class(business_area_code=test_business_area_code, filename=None)

        self.assertEqual('You need provide the path to the file', str(context_manager.exception))

    @mock.patch('unicef_vision.synchronizers.logger.info')
    def test_instantiation_positive(self, mock_logger_info):
        """Exercise successfully creating a synchronizer"""
        test_business_area_code = 'ABC'
        test_filename = 'tests/test.json'

        self.synchronizer_class(business_area_code=test_business_area_code, filename=test_filename)

        # Ensure msgs are logged
        self.assertEqual(mock_logger_info.call_count, 2)
        expected_msg = 'Synchronizer is FileDataSynchronizer'
        self.assertEqual(mock_logger_info.call_args_list[0][0], (expected_msg, ))
        self.assertEqual(mock_logger_info.call_args_list[0][1], {})

        expected_msg = 'business_area_code is ' + test_business_area_code
        self.assertEqual(mock_logger_info.call_args_list[1][0], (expected_msg, ))
        self.assertEqual(mock_logger_info.call_args_list[1][1], {})


class TestMultiModelDataSynchronizer(TestCase):

    def setUp(self):
        test_business_area_code = 'ABC'
        self.synchronizer_class = MultiModelDataSynchronizer
        self.synchronizer_class.ENDPOINT = 'GetSomeStuff_JSON'

        self.synchronizer = self.synchronizer_class(business_area_code=test_business_area_code)

    def test_convert_records(self):
        list_records = [1,2,3]
        self.assertEqual(list_records, self.synchronizer._convert_records(list_records))
        list_records_str = '[1, 2, 3]'
        self.assertEqual(list_records, self.synchronizer._convert_records(list_records_str))
        self.assertListEqual([], self.synchronizer._convert_records('abcde'))


class TestManualVisionSynchronizer(TestCase):
    """Exercise initialization of ManualVisionSynchronizer class"""

    def setUp(self):
        self.synchronizer_class = ManualVisionSynchronizer
        self.synchronizer_class.ENDPOINT = 'GetSomeStuff_JSON'

    def _setup_sync(self):
        """set up syncronyzer class defaults and mappings"""
        self.synchronizer_class.REQUIRED_KEYS = (
            "VENDOR_CODE",
            "VENDOR_NAME",
            "date",
        )
        self.synchronizer_class.MAPPING = {
            'partner': {
                "code": "VENDOR_CODE",
                "name": "VENDOR_NAME",
                "desc": "DESCRIPTION",
                "date": "date",
                "blocked": "blocked",
            },
        }
        self.synchronizer_class.DATE_FIELDS = ['date']
        self.synchronizer_class.FIELD_HANDLERS = {
            'partner': {
                "blocked": lambda x: True if x else False,
            }
        }
        self.synchronizer_class.MODEL_MAPPING = OrderedDict((
            ('partner', mock.Mock()),
        ))

    def _setup_sync_mapping_v1(self):
        self._setup_sync()

    def _setup_sync_mapping_v2(self):
        """set up partner model as callable of type types.FunctionType"""
        def f_type(): pass

        self._setup_sync()

        self.synchronizer_class.MAPPING = {
            'partner': {
                "partner": "partner",
                "code": "VENDOR_CODE",
                "name": "VENDOR_NAME",
                "date": "date",
            },
        }
        self.synchronizer_class.MODEL_MAPPING = OrderedDict((
            ('partner', f_type),
        ))

    def _setup_sync_mapping_v3(self):
        """set up test data as queryable fields of partner model class"""

        self._setup_sync()
        self.synchronizer_class.MAPPING = {
            'partner': {
                "partner": "partner",
                "code": "VENDOR_CODE",
                "name": "VENDOR_NAME",
                "date": "date",
            },
        }
        self.synchronizer_class.MODEL_MAPPING = OrderedDict((
            ('partner', {
                "code": "t1",
                "name": "n1",
                "date": "/Date(1375243200000)/"
            }),
        ))

    def _setup_sync_mapping_v4(self):
        """set up test data to break into the `unique_together` check of the `_process_record` call"""

        def get_m_field(field):
            return m._meta.fields[field]

        self._setup_sync()
        self.synchronizer_class.MAPPING = {
            'partner': {
                "code": "VENDOR_CODE",
                "name": "VENDOR_NAME",
                "date": "date",
            },
        }

        m = mock.Mock(spec=['_meta'])
        m._meta.fields = {}
        m._meta.get_field = get_m_field

        for value in self.synchronizer_class.MAPPING['partner'].keys():
            mval = mock.Mock(spec=[value], value=value)
            setattr(mval, 'unique', False)
            m._meta.fields[value] = mval

        self.synchronizer_class.m = m
        self.synchronizer_class.MODEL_MAPPING = OrderedDict((
            ('partner', m),
        ))

    def _setup_test_records(self):
        """set up samples of imported JSON data"""
        return [
            {
                "partner": 1,
                "VENDOR_CODE": "t1",
                "VENDOR_NAME": "n1",
                "DESCRIPTION": "desc",
                "date": "/Date(1375243200000)/",
            }, {
                "partner": 2,
                "VENDOR_CODE": "t2",
                "VENDOR_NAME": "",
                "date": "/Date(1375243200000)/",
                "blocked": True,
            }, {
                "code": "bad_key",
                "name": "bad_key",
                "date": "/Date(1375243200000)/"
            },
        ]

    def test_instantiation_no_business_area_code(self):
        """Ensure I can't create a synchronizer without specifying a business_area_code"""
        with self.assertRaises(VisionException) as context_manager:
            self.synchronizer_class()

        self.assertEqual('business_area_code is required', str(context_manager.exception))

    def test_instantiation_object_number_no_endpoint(self):
        test_business_area_code = 'ABC'
        test_object_number = 1

        class _MyBadSynchronizer(self.synchronizer_class):
            """Synchronizer class that doesn't set self.ENDPOINT"""
            ENDPOINT = None

        with self.assertRaises(VisionException) as context_manager:
            _MyBadSynchronizer(business_area_code=test_business_area_code, object_number=test_object_number)

        self.assertEqual('You must set the ENDPOINT name', str(context_manager.exception))

    @mock.patch('unicef_vision.synchronizers.logger.info')
    def test_instantiation_positive_with_object_number(self, mock_logger_info):
        """Exercise successfully creating a synchronizer"""
        test_business_area_code = 'ABC'
        test_object_number = 1

        self.synchronizer_class(business_area_code=test_business_area_code, object_number=test_object_number)

        # Ensure correct initialisation by checking logs
        self.assertEqual(mock_logger_info.call_count, 1)

    def test_save_records_mapping_v1(self):
        self._setup_sync_mapping_v1()
        test_records = self._setup_test_records()

        syncronizer = self.synchronizer_class(business_area_code='ABC')
        syncronizer._save_records(test_records)

    def test_save_records_mapping_v2(self):
        """test with MODEL_MAPPING as a callable function"""
        self._setup_sync_mapping_v2()
        test_records = self._setup_test_records()

        syncronizer = self.synchronizer_class(business_area_code='ABC')
        syncronizer._save_records(test_records)

    def test_save_records_mapping_v3(self):
        """test with MODEL_MAPPING as a hard-coded set"""
        self._setup_sync_mapping_v3()
        test_records = self._setup_test_records()

        syncronizer = self.synchronizer_class(business_area_code='ABC')
        syncronizer._save_records(test_records)

    def test_save_records_mapping_v4(self):
        """test with MODEL_MAPPING as a Mock with filled model `unique`, `unique_together` and field `defaults`"""
        self._setup_sync_mapping_v4()
        test_records = self._setup_test_records()

        # test with full `unique_together`
        syncronizer = self.synchronizer_class(business_area_code='ABC')
        syncronizer.m._meta.unique_together = [syncronizer.MAPPING['partner'].keys()]
        syncronizer._save_records(test_records)

        # test partial `unique_together`
        syncronizer.m._meta.unique_together = ['code', 'name']
        syncronizer._save_records(test_records)

        # add back 'desc' to the mapping to test when it's missing and it's also NOT_PROVIDED
        self.synchronizer_class.MAPPING['partner']['desc'] = 'desc'
        syncronizer.m._meta.fields['desc'] = mock.Mock(spec=['desc'], value='desc')
        setattr(syncronizer.m._meta.fields['desc'], 'default', NOT_PROVIDED)
        syncronizer._save_records(test_records)
