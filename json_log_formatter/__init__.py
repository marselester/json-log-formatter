from typing import Any

import logging
from datetime import datetime, timezone
from decimal import Decimal
import json
from types import ModuleType


BUILTIN_ATTRS: set[str] = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "taskName",
    "thread",
    "threadName",
}


class JSONFormatter(logging.Formatter):
    """JSON log formatter.

    Usage example::

        import logging

        import json_log_formatter

        json_handler = logging.FileHandler(filename='/var/log/my-log.json')
        json_handler.setFormatter(json_log_formatter.JSONFormatter())

        logger = logging.getLogger('my_json')
        logger.addHandler(json_handler)

        logger.info('Sign up', extra={'referral_code': '52d6ce'})

    The log file will contain the following log record (inline)::

        {
            "message": "Sign up",
            "time": "2015-09-01T06:06:26.524448",
            "referral_code": "52d6ce"
        }

    """

    json_lib: ModuleType = json

    def format(self, record: logging.LogRecord) -> Any | str:
        message: str = record.getMessage()
        extra: dict[str, Any] = self.extra_from_record(record)
        json_record: dict[str, Any] = self.json_record(message, extra, record)
        mutated_record: dict[str, Any] = self.mutate_json_record(json_record)
        # Backwards compatibility: Functions that overwrite this but don't
        # return a new value will return None because they modified the
        # argument passed in.
        if mutated_record is None:
            mutated_record = json_record
        return self.to_json(mutated_record)

    def to_json(self, record: dict[str, Any]) -> Any | str:
        """Converts record dict to a JSON string.

        It makes best effort to serialize a record (represents an object as a string)
        instead of raising TypeError if json library supports default argument.
        Note, ujson doesn't support it.
        ValueError and OverflowError are also caught to avoid crashing an app,
        e.g., due to circular reference.

        Override this method to change the way dict is converted to JSON.

        """
        try:
            return self.json_lib.dumps(record, default=_json_serializable)
        # ujson doesn't support default argument and raises TypeError.
        # "ValueError: Circular reference detected" is raised
        # when there is a reference to object inside the object itself.
        except (TypeError, ValueError, OverflowError):
            try:
                return self.json_lib.dumps(record)
            except (TypeError, ValueError, OverflowError):
                return "{}"

    def extra_from_record(self, record: logging.LogRecord) -> dict[str, Any]:
        """Returns `extra` dict you passed to logger.

        The `extra` keyword argument is used to populate the `__dict__` of
        the `LogRecord`.

        """
        return {
            attr_name: record.__dict__[attr_name]
            for attr_name in record.__dict__
            if attr_name not in BUILTIN_ATTRS
        }

    def json_record(
        self, message: str, extra: dict[str, Any], record: logging.LogRecord
    ) -> dict[str, Any]:
        """Prepares a JSON payload which will be logged.

        Override this method to change JSON log format.

        :param message: Log message, e.g., `logger.info(msg='Sign up')`.
        :param extra: Dictionary that was passed as `extra` param
            `logger.info('Sign up', extra={'referral_code': '52d6ce'})`.
        :param record: `LogRecord` we got from `JSONFormatter.format()`.
        :return: Dictionary which will be passed to JSON lib.

        """
        extra["message"] = message
        if "time" not in extra:
            extra["time"] = datetime.now(timezone.utc)

        if record.exc_info:
            extra["exc_info"] = self.formatException(record.exc_info)

        return extra

    def mutate_json_record(self, json_record: dict[str, Any]) -> dict[str, Any]:
        """Override it to convert fields of `json_record` to needed types.

        Default implementation converts `datetime` to string in ISO8601 format.

        """
        for attr_name in json_record:
            attr = json_record[attr_name]
            if isinstance(attr, datetime):
                json_record[attr_name] = attr.isoformat()
        return json_record


def _json_serializable(obj: Any) -> Any:
    try:
        return obj.__dict__
    except AttributeError:
        return str(obj)


class VerboseJSONFormatter(JSONFormatter):
    """JSON log formatter with built-in log record attributes such as log level.

    Usage example::

        import logging

        import json_log_formatter

        json_handler = logging.FileHandler(filename='/var/log/my-log.json')
        json_handler.setFormatter(json_log_formatter.VerboseJSONFormatter())

        logger = logging.getLogger('my_verbose_json')
        logger.addHandler(json_handler)

        logger.error('An error has occured')

    The log file will contain the following log record (inline)::

        {
            "filename": "tests.py",
            "funcName": "test_file_name_is_testspy",
            "levelname": "ERROR",
            "lineno": 276,
            "module": "tests",
            "name": "my_verbose_json",
            "pathname": "/Users/bob/json-log-formatter/tests.py",
            "process": 3081,
            "processName": "MainProcess",
            "stack_info": null,
            "thread": 4664270272,
            "threadName": "MainThread",
            "message": "An error has occured",
            "time": "2021-07-04T21:05:42.767726"
        }

    Read more about the built-in log record attributes
    https://docs.python.org/3/library/logging.html#logrecord-attributes.

    """

    def json_record(
        self, message: str, extra: dict[str, Any], record: logging.LogRecord
    ) -> dict[str, Any]:
        extra.update(
            {
                "filename": record.filename,
                "funcName": record.funcName,
                "levelname": record.levelname,
                "lineno": record.lineno,
                "module": record.module,
                "name": record.name,
                "pathname": record.pathname,
                "process": record.process,
                "processName": record.processName,
                "stack_info": record.stack_info
                if hasattr(record, "stack_info")
                else None,
                "thread": record.thread,
                "threadName": record.threadName,
            }
        )
        return super().json_record(message, extra, record)


class FlatJSONFormatter(JSONFormatter):
    """Flat JSON log formatter ensures that complex objects are stored as strings.

    Usage example::

        logger.info('Sign up', extra={'request': WSGIRequest({
            'PATH_INFO': 'bogus',
            'REQUEST_METHOD': 'bogus',
            'CONTENT_TYPE': 'text/html; charset=utf8',
            'wsgi.input': BytesIO(b''),
        })})

    The log file will contain the following log record (inline)::

        {
            "message": "Sign up",
            "time": "2024-10-01T00:59:29.332888+00:00",
            "request": "<WSGIRequest: BOGUS '/bogus'>"
        }

    """

    keep: tuple[type, ...] = (bool, int, float, Decimal, complex, str, datetime)

    def json_record(
        self, message: str, extra: dict[str, Any], record: logging.LogRecord
    ) -> dict[str, Any]:
        extra = super().json_record(message, extra, record)
        return {
            k: v if v is None or isinstance(v, self.keep) else str(v)
            for k, v in extra.items()
        }
