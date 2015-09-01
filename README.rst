==================
JSON log formatter
==================

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

The log file will contain the following log record (inline)::

    {
        "message": "Sign up",
        "time": "2015-09-01T06:06:26.524448",
        "referral_code": "52d6ce"
    }

Tests
-----

.. code-block:: console

    $ pip install -r requirements.txt
    $ tox
