import unittest
import logging
from datetime import datetime
from decimal import Decimal

import json
import ujson
import simplejson

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

from json_log_formatter import JSONFormatter

log_buffer = StringIO()
json_handler = logging.StreamHandler(log_buffer)

logger = logging.getLogger('test')
logger.addHandler(json_handler)
logger.setLevel(logging.DEBUG)
logging.propagate = False

DATETIME = datetime(2015, 9, 1, 6, 9, 42, 797203)
DATETIME_ISO = u'2015-09-01T06:09:42.797203'


class TestCase(unittest.TestCase):
    def tearDown(self):
        log_buffer.seek(0)
        log_buffer.truncate()


class JSONFormatterTest(TestCase):
    def setUp(self):
        json_handler.setFormatter(JSONFormatter())

    def test_given_time_is_used_in_log_record(self):
        logger.info('Sign up', extra={'time': DATETIME})
        expected_time = '"time": "2015-09-01T06:09:42.797203"'
        self.assertIn(expected_time, log_buffer.getvalue())

    def test_current_time_is_used_by_default_in_log_record(self):
        logger.info('Sign up', extra={'fizz': 'bazz'})
        self.assertNotIn(DATETIME_ISO, log_buffer.getvalue())

    def test_message_and_time_are_in_json_record_when_extra_is_blank(self):
        logger.info('Sign up')
        json_record = json.loads(log_buffer.getvalue())
        expected_fields = set([
            'message',
            'time',
        ])
        self.assertEqual(set(json_record), expected_fields)

    def test_message_and_time_and_extra_are_in_json_record_when_extra_is_provided(self):
        logger.info('Sign up', extra={'fizz': 'bazz'})
        json_record = json.loads(log_buffer.getvalue())
        expected_fields = set([
            'message',
            'time',
            'fizz',
        ])
        self.assertEqual(set(json_record), expected_fields)


class MutatingFormatter(JSONFormatter):
    def mutate_json_record(self, json_record):
        new_record = {}
        for k, v in json_record.items():
            if isinstance(v, datetime):
                v = v.isoformat()
            new_record[k] = v
        return new_record


class MutatingFormatterTest(TestCase):
    def setUp(self):
        json_handler.setFormatter(MutatingFormatter())

    def test_new_record_accepted(self):
        logger.info('Sign up', extra={'fizz': DATETIME})
        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record['fizz'], DATETIME_ISO)


class JsonLibTest(TestCase):
    def setUp(self):
        json_handler.setFormatter(JSONFormatter())

    def test_error_when_decimal_is_passed(self):
        with self.assertRaises(TypeError):
            logger.log(lvl=0, msg='Payment was sent', extra={
                'amount': Decimal('0.00497265')
            })


class UjsonLibTest(TestCase):
    def setUp(self):
        formatter = JSONFormatter()
        formatter.json_lib = ujson
        json_handler.setFormatter(formatter)

    def test_decimal_is_serialized_as_number(self):
        logger.info('Payment was sent', extra={
            'amount': Decimal('0.00497265')
        })
        expected_amount = '"amount":0.00497265'
        self.assertIn(expected_amount, log_buffer.getvalue())

    def test_zero_expected_when_decimal_is_in_scientific_notation(self):
        logger.info('Payment was sent', extra={
            'amount': Decimal('0E-8')
        })
        expected_amount = '"amount":0.0'
        self.assertIn(expected_amount, log_buffer.getvalue())


class SimplejsonLibTest(TestCase):
    def setUp(self):
        formatter = JSONFormatter()
        formatter.json_lib = simplejson
        json_handler.setFormatter(formatter)

    def test_decimal_is_serialized_as_number(self):
        logger.info('Payment was sent', extra={
            'amount': Decimal('0.00497265')
        })
        expected_amount = '"amount": 0.00497265'
        self.assertIn(expected_amount, log_buffer.getvalue())

    def test_decimal_is_serialized_as_it_is_when_it_is_in_scientific_notation(self):
        logger.info('Payment was sent', extra={
            'amount': Decimal('0E-8')
        })
        expected_amount = '"amount": 0E-8'
        self.assertIn(expected_amount, log_buffer.getvalue())
