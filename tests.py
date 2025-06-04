from datetime import datetime
from decimal import Decimal
from io import BytesIO
import unittest
from typing import Any
import logging
import json
import os.path


from django.core.handlers.wsgi import WSGIRequest
from django.conf import settings
import ujson  # type: ignore
import simplejson  # type: ignore

try:
    from cStringIO import StringIO  # type: ignore
except ImportError:
    from io import StringIO

from json_log_formatter import JSONFormatter, VerboseJSONFormatter, FlatJSONFormatter

log_buffer = StringIO()
json_handler = logging.StreamHandler(log_buffer)

logger = logging.getLogger("test")
logger.addHandler(json_handler)
logger.setLevel(logging.DEBUG)
logger.propagate = False

DATETIME = datetime(2015, 9, 1, 6, 9, 42, 797203)
DATETIME_ISO = "2015-09-01T06:09:42.797203"

settings.configure(DEBUG=True)


class TestCase(unittest.TestCase):
    def tearDown(self) -> None:
        log_buffer.seek(0)
        log_buffer.truncate()


class JSONFormatterTest(TestCase):
    def setUp(self) -> None:
        json_handler.setFormatter(JSONFormatter())

    def test_given_time_is_used_in_log_record(self) -> None:
        logger.info("Sign up", extra={"time": DATETIME})
        expected_time = '"time": "2015-09-01T06:09:42.797203"'
        self.assertIn(expected_time, log_buffer.getvalue())

    def test_current_time_is_used_by_default_in_log_record(self) -> None:
        logger.info("Sign up", extra={"fizz": "bazz"})
        self.assertNotIn(DATETIME_ISO, log_buffer.getvalue())

    def test_message_and_time_are_in_json_record_when_extra_is_blank(self) -> None:
        logger.info("Sign up")
        json_record = json.loads(log_buffer.getvalue())
        expected_fields = set(
            [
                "message",
                "time",
            ]
        )
        self.assertTrue(expected_fields.issubset(json_record))

    def test_message_and_time_and_extra_are_in_json_record_when_extra_is_provided(
        self,
    ) -> None:
        logger.info("Sign up", extra={"fizz": "bazz"})
        json_record = json.loads(log_buffer.getvalue())
        expected_fields = set(
            [
                "message",
                "time",
                "fizz",
            ]
        )
        self.assertTrue(expected_fields.issubset(json_record))

    def test_exc_info_is_logged(self) -> None:
        try:
            raise ValueError("something wrong")
        except ValueError:
            logger.error("Request failed", exc_info=True)
        json_record = json.loads(log_buffer.getvalue())
        self.assertIn("Traceback (most recent call last)", json_record["exc_info"])


class MutatingFormatter(JSONFormatter):
    def mutate_json_record(self, json_record: dict[str, Any]) -> dict[str, Any]:
        new_record = {}
        for k, v in json_record.items():
            if isinstance(v, datetime):
                v = v.isoformat()
            new_record[k] = v
        return new_record


class MutatingFormatterTest(TestCase):
    def setUp(self) -> None:
        json_handler.setFormatter(MutatingFormatter())

    def test_new_record_accepted(self) -> None:
        logger.info("Sign up", extra={"fizz": DATETIME})
        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["fizz"], DATETIME_ISO)


class JsonLibTest(TestCase):
    def setUp(self) -> None:
        json_handler.setFormatter(JSONFormatter())

    def test_builtin_types_are_serialized(self) -> None:
        logger.log(
            level=logging.ERROR,
            msg="Payment was sent",
            extra={
                "first_name": "bob",
                "amount": 0.00497265,
                "context": {
                    "tags": ["fizz", "bazz"],
                },
                "things": ("a", "b"),
                "ok": True,
                "none": None,
            },
        )

        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["first_name"], "bob")
        self.assertEqual(json_record["amount"], 0.00497265)
        self.assertEqual(json_record["context"], {"tags": ["fizz", "bazz"]})
        self.assertEqual(json_record["things"], ["a", "b"])
        self.assertEqual(json_record["ok"], True)
        self.assertEqual(json_record["none"], None)

    def test_decimal_is_serialized_as_string(self) -> None:
        logger.log(
            level=logging.ERROR,
            msg="Payment was sent",
            extra={"amount": Decimal("0.00497265")},
        )
        expected_amount = '"amount": "0.00497265"'
        self.assertIn(expected_amount, log_buffer.getvalue())

    def test_django_wsgi_request_is_serialized_as_dict(self) -> None:
        request = WSGIRequest(
            {
                "PATH_INFO": "bogus",
                "REQUEST_METHOD": "bogus",
                "CONTENT_TYPE": "text/html; charset=utf8",
                "wsgi.input": BytesIO(b""),
            }
        )

        logger.log(
            level=logging.ERROR,
            msg="Django response error",
            extra={"status_code": 500, "request": request},
        )
        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["status_code"], 500)
        self.assertEqual(json_record["request"]["path"], "/bogus")
        self.assertEqual(json_record["request"]["method"], "BOGUS")

    def test_json_circular_reference_is_handled(self) -> None:
        d: dict[str, object] = {}
        d["circle"] = d
        logger.info("Referer checking", extra=d)
        self.assertEqual("{}\n", log_buffer.getvalue())


class UjsonLibTest(TestCase):
    def setUp(self) -> None:
        formatter = JSONFormatter()
        formatter.json_lib = ujson
        json_handler.setFormatter(formatter)

    def test_builtin_types_are_serialized(self) -> None:
        logger.log(
            level=logging.ERROR,
            msg="Payment was sent",
            extra={
                "first_name": "bob",
                "amount": 0.00497265,
                "context": {
                    "tags": ["fizz", "bazz"],
                },
                "things": ("a", "b"),
                "ok": True,
                "none": None,
            },
        )

        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["first_name"], "bob")
        self.assertEqual(json_record["amount"], 0.00497265)
        self.assertEqual(json_record["context"], {"tags": ["fizz", "bazz"]})
        self.assertEqual(json_record["things"], ["a", "b"])
        self.assertEqual(json_record["ok"], True)
        self.assertEqual(json_record["none"], None)

    def test_decimal_is_serialized_as_number(self) -> None:
        logger.info("Payment was sent", extra={"amount": Decimal("0.00497265")})
        expected_amount = '"amount":0.00497265'
        self.assertIn(expected_amount, log_buffer.getvalue())

    def test_zero_expected_when_decimal_is_in_scientific_notation(self) -> None:
        logger.info("Payment was sent", extra={"amount": Decimal("0E-8")})
        expected_amount = '"amount":0.0'
        self.assertIn(expected_amount, log_buffer.getvalue())

    def test_django_wsgi_request_is_serialized_as_empty_list(self) -> None:
        request = WSGIRequest(
            {
                "PATH_INFO": "bogus",
                "REQUEST_METHOD": "bogus",
                "CONTENT_TYPE": "text/html; charset=utf8",
                "wsgi.input": BytesIO(b""),
            }
        )

        logger.log(
            level=logging.ERROR,
            msg="Django response error",
            extra={"status_code": 500, "request": request},
        )
        json_record = json.loads(log_buffer.getvalue())
        if "status_code" in json_record:
            self.assertEqual(json_record["status_code"], 500)
        if "request" in json_record:
            self.assertEqual(json_record["request"]["path"], "/bogus")
            self.assertEqual(json_record["request"]["method"], "BOGUS")

    def test_json_circular_reference_is_handled(self) -> None:
        d: dict[str, object] = {}
        d["circle"] = d
        logger.info("Referer checking", extra=d)
        self.assertEqual("{}\n", log_buffer.getvalue())


class SimplejsonLibTest(TestCase):
    def setUp(self) -> None:
        formatter = JSONFormatter()
        formatter.json_lib = simplejson
        json_handler.setFormatter(formatter)

    def test_builtin_types_are_serialized(self) -> None:
        logger.log(
            level=logging.ERROR,
            msg="Payment was sent",
            extra={
                "first_name": "bob",
                "amount": 0.00497265,
                "context": {
                    "tags": ["fizz", "bazz"],
                },
                "things": ("a", "b"),
                "ok": True,
                "none": None,
            },
        )

        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["first_name"], "bob")
        self.assertEqual(json_record["amount"], 0.00497265)
        self.assertEqual(json_record["context"], {"tags": ["fizz", "bazz"]})
        self.assertEqual(json_record["things"], ["a", "b"])
        self.assertEqual(json_record["ok"], True)
        self.assertEqual(json_record["none"], None)

    def test_decimal_is_serialized_as_number(self) -> None:
        logger.info("Payment was sent", extra={"amount": Decimal("0.00497265")})
        expected_amount = '"amount": 0.00497265'
        self.assertIn(expected_amount, log_buffer.getvalue())

    def test_decimal_is_serialized_as_it_is_when_it_is_in_scientific_notation(
        self,
    ) -> None:
        logger.info("Payment was sent", extra={"amount": Decimal("0E-8")})
        expected_amount = '"amount": 0E-8'
        self.assertIn(expected_amount, log_buffer.getvalue())

    def test_django_wsgi_request_is_serialized_as_dict(self) -> None:
        request = WSGIRequest(
            {
                "PATH_INFO": "bogus",
                "REQUEST_METHOD": "bogus",
                "CONTENT_TYPE": "text/html; charset=utf8",
                "wsgi.input": BytesIO(b""),
            }
        )

        logger.log(
            level=logging.ERROR,
            msg="Django response error",
            extra={"status_code": 500, "request": request},
        )
        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["status_code"], 500)
        self.assertEqual(json_record["request"]["path"], "/bogus")
        self.assertEqual(json_record["request"]["method"], "BOGUS")

    def test_json_circular_reference_is_handled(self) -> None:
        d: dict[str, object] = {}
        d["circle"] = d
        logger.info("Referer checking", extra=d)
        self.assertEqual("{}\n", log_buffer.getvalue())


class VerboseJSONFormatterTest(TestCase):
    def setUp(self) -> None:
        json_handler.setFormatter(VerboseJSONFormatter())

    def test_file_name_is_testspy(self) -> None:
        logger.error("An error has occured")
        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["filename"], "tests.py")

    def test_function_name(self) -> None:
        logger.error("An error has occured")
        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["funcName"], "test_function_name")

    def test_level_name_is_error(self) -> None:
        logger.error("An error has occured")
        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["levelname"], "ERROR")

    def test_module_name_is_tests(self) -> None:
        logger.error("An error has occured")
        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["module"], "tests")

    def test_logger_name_is_test(self) -> None:
        logger.error("An error has occured")
        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["name"], "test")

    def test_path_name_is_test(self) -> None:
        logger.error("An error has occured")
        json_record = json.loads(log_buffer.getvalue())
        self.assertIn(
            os.path.basename(os.path.abspath(".")) + "/tests.py",
            json_record["pathname"],
        )

    def test_process_name_is_MainProcess(self) -> None:
        logger.error("An error has occured")
        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["processName"], "MainProcess")

    def test_thread_name_is_MainThread(self) -> None:
        logger.error("An error has occured")
        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["threadName"], "MainThread")

    def test_stack_info_is_none(self) -> None:
        logger.error("An error has occured")
        json_record = json.loads(log_buffer.getvalue())
        self.assertIsNone(json_record["stack_info"])


class FlatJSONFormatterTest(TestCase):
    def setUp(self) -> None:
        json_handler.setFormatter(FlatJSONFormatter())

    def test_given_time_is_used_in_log_record(self) -> None:
        logger.info("Sign up", extra={"time": DATETIME})
        expected_time = '"time": "2015-09-01T06:09:42.797203"'
        self.assertIn(expected_time, log_buffer.getvalue())

    def test_current_time_is_used_by_default_in_log_record(self) -> None:
        logger.info("Sign up", extra={"fizz": "bazz"})
        self.assertNotIn(DATETIME_ISO, log_buffer.getvalue())

    def test_message_and_time_are_in_json_record_when_extra_is_blank(self) -> None:
        logger.info("Sign up")
        json_record = json.loads(log_buffer.getvalue())
        expected_fields = set(
            [
                "message",
                "time",
            ]
        )
        self.assertTrue(expected_fields.issubset(json_record))

    def test_message_and_time_and_extra_are_in_json_record_when_extra_is_provided(
        self,
    ) -> None:
        logger.info("Sign up", extra={"fizz": "bazz"})
        json_record = json.loads(log_buffer.getvalue())
        expected_fields = set(
            [
                "message",
                "time",
                "fizz",
            ]
        )
        self.assertTrue(expected_fields.issubset(json_record))

    def test_exc_info_is_logged(self) -> None:
        try:
            raise ValueError("something wrong")
        except ValueError:
            logger.error("Request failed", exc_info=True)
        json_record = json.loads(log_buffer.getvalue())
        self.assertIn("Traceback (most recent call last)", json_record["exc_info"])

    def test_builtin_types_are_serialized(self) -> None:
        logger.log(
            level=logging.ERROR,
            msg="Payment was sent",
            extra={
                "first_name": "bob",
                "amount": 0.00497265,
                "context": {
                    "tags": ["fizz", "bazz"],
                },
                "things": ("a", "b"),
                "ok": True,
                "none": None,
            },
        )

        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["first_name"], "bob")
        self.assertEqual(json_record["amount"], 0.00497265)
        self.assertEqual(json_record["context"], "{'tags': ['fizz', 'bazz']}")
        self.assertEqual(json_record["things"], "('a', 'b')")
        self.assertEqual(json_record["ok"], True)
        self.assertEqual(json_record["none"], None)

    def test_decimal_is_serialized_as_string(self) -> None:
        logger.log(
            level=logging.ERROR,
            msg="Payment was sent",
            extra={"amount": Decimal("0.00497265")},
        )
        expected_amount = '"amount": "0.00497265"'
        self.assertIn(expected_amount, log_buffer.getvalue())

    def test_django_wsgi_request_is_serialized_as_dict(self) -> None:
        request = WSGIRequest(
            {
                "PATH_INFO": "bogus",
                "REQUEST_METHOD": "bogus",
                "CONTENT_TYPE": "text/html; charset=utf8",
                "wsgi.input": BytesIO(b""),
            }
        )

        logger.log(
            level=logging.ERROR,
            msg="Django response error",
            extra={
                "status_code": 500,
                "request": request,
                "dict": {
                    "request": request,
                },
                "list": [request],
            },
        )
        json_record = json.loads(log_buffer.getvalue())
        self.assertEqual(json_record["status_code"], 500)
        self.assertEqual(json_record["request"], "<WSGIRequest: BOGUS '/bogus'>")
        self.assertEqual(
            json_record["dict"], "{'request': <WSGIRequest: BOGUS '/bogus'>}"
        )
        self.assertEqual(json_record["list"], "[<WSGIRequest: BOGUS '/bogus'>]")
