==================
JSON log formatter
==================

.. image:: https://travis-ci.org/marselester/json-log-formatter.png
   :target: https://travis-ci.org/marselester/json-log-formatter

The library helps you to store logs in JSON format. Why is it important?
Well, it facilitates integration with **Logstash**.

Usage example:

.. code-block:: python

    import logging

    import json_log_formatter

    formatter = json_log_formatter.JSONFormatter()

    json_handler = logging.FileHandler(filename='/var/log/my-log.json')
    json_handler.setFormatter(formatter)

    logger = logging.getLogger('my_json')
    logger.addHandler(json_handler)
    logger.setLevel(logging.INFO)

    logger.info('Sign up', extra={'referral_code': '52d6ce'})

    try:
        raise ValueError('something wrong')
    except ValueError:
        logger.error('Request failed', exc_info=True)

The log file will contain the following log record (inline).

.. code-block:: json

    {
        "message": "Sign up",
        "time": "2015-09-01T06:06:26.524448",
        "referral_code": "52d6ce"
    }
    {
        "message": "Request failed",
        "time": "2015-09-01T06:06:26.524449",
        "exc_info": "Traceback (most recent call last): ..."
    }

If you use a log collection and analysis system,
you might need to include the built-in
`log record attributes <https://docs.python.org/3/library/logging.html#logrecord-attributes>`_
with ``VerboseJSONFormatter``.

.. code-block:: python

    json_handler.setFormatter(json_log_formatter.VerboseJSONFormatter())
    logger.error('An error has occured')

.. code-block:: json

    {
        "filename": "tests.py",
        "funcName": "test_file_name_is_testspy",
        "levelname": "ERROR",
        "lineno": 276,
        "module": "tests",
        "name": "my_json",
        "pathname": "/Users/bob/json-log-formatter/tests.py",
        "process": 3081,
        "processName": "MainProcess",
        "stack_info": null,
        "thread": 4664270272,
        "threadName": "MainThread",
        "message": "An error has occured",
        "time": "2021-07-04T21:05:42.767726"
    }

JSON libraries
--------------

You can use **ujson** or **simplejson** instead of built-in **json** library.

.. code-block:: python

    import json_log_formatter
    import ujson

    formatter = json_log_formatter.JSONFormatter()
    formatter.json_lib = ujson

Note, **ujson** doesn't support ``dumps(default=f)`` argument:
if it can't serialize an attribute, it might fail with ``TypeError`` or skip an attribute.

Django integration
------------------

Here is an example of how the JSON formatter can be used with Django.

.. code-block:: python

    LOGGING['formatters']['json'] = {
        '()': 'json_log_formatter.JSONFormatter',
    }
    LOGGING['handlers']['json_file'] = {
        'level': 'INFO',
        'class': 'logging.FileHandler',
        'filename': '/var/log/my-log.json',
        'formatter': 'json',
    }
    LOGGING['loggers']['my_json'] = {
        'handlers': ['json_file'],
        'level': 'INFO',
    }

Let's try to log something.

.. code-block:: python

    import logging

    logger = logging.getLogger('my_json')

    logger.info('Sign up', extra={'referral_code': '52d6ce'})

Custom formatter
----------------

You will likely need a custom log formatter. For instance, you want to log
a user ID, an IP address and ``time`` as ``django.utils.timezone.now()``.
To do so you should override ``JSONFormatter.json_record()``.

.. code-block:: python

    class CustomisedJSONFormatter(json_log_formatter.JSONFormatter):
        def json_record(self, message: str, extra: dict, record: logging.LogRecord) -> dict:
            extra['message'] = message
            extra['user_id'] = current_user_id()
            extra['ip'] = current_ip()

            # Include builtins
            extra['level'] = record.levelname
            extra['name'] = record.name

            if 'time' not in extra:
                extra['time'] = django.utils.timezone.now()

            if record.exc_info:
                extra['exc_info'] = self.formatException(record.exc_info)

            return extra

Let's say you want ``datetime`` to be serialized as timestamp.
You can use **ujson** (which does it by default) and disable
ISO8601 date mutation.

.. code-block:: python

    class CustomisedJSONFormatter(json_log_formatter.JSONFormatter):
        json_lib = ujson

        def mutate_json_record(self, json_record):
            return json_record

Tests
-----

.. code-block:: console

    $ pip install -r requirements.txt
    $ tox
