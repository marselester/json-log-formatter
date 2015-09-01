==================
JSON log formatter
==================

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

    logger.info('Sign up', extra={'referral_code': '52d6ce'})

The log file will contain the following log record (inline).

.. code-block:: json

    {
        "message": "Sign up",
        "time": "2015-09-01T06:06:26.524448",
        "referral_code": "52d6ce"
    }

JSON libraries
--------------

You can use **ujson** or **simplejson** instead of built-in **json** library.
They are faster and can serialize `Decimal` values.

.. code-block:: python

    import json_log_formatter
    import ujson

    formatter = json_log_formatter.JSONFormatter()
    formatter.json_lib = ujson

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

Tests
-----

.. code-block:: console

    $ pip install -r requirements.txt
    $ tox
