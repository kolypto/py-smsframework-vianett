[![Build Status](https://api.travis-ci.org/kolypto/py-smsframework-vianett.png?branch=master)](https://travis-ci.org/kolypto/py-smsframework-vianett)
[![Pythons](https://img.shields.io/badge/python-2.7%20%7C%203.4%E2%80%933.7%20%7C%20pypy-blue.svg)](.travis.yml)


SMSframework Vianett Provider
================================

[Vianett](http://www.vianett.com/) Provider for [smsframework](https://pypi.python.org/pypi/smsframework/).

You need an account with "SMS Server" service set up.
You'll need the following configuration: username, password.






Installation
============

Install from pypi:

    $ pip install smsframework_vianett

To receive SMS messages, you need to ensure that
[Flask microframework](http://flask.pocoo.org) is also installed:


    $ pip install smsframework_vianett[receiver]






Initialization
==============

```python
from smsframework import Gateway
from smsframework_vianett import VianettProvider

gateway = Gateway()
gateway.add_provider('vianett', VianettProvider,
    user='kolypto',
    password='123',
    https=False,
    use_prefix=True
)
```

Config
------

Source: /smsframework_vianett/provider.py

* `user: str`: Account username
* `password: str`: Account password
* `https: bool`: Use HTTPS for outgoing messages? Default: `False`
* `use_prefix: bool`: Do you use prefixes for incoming messages?

    Stupidly, Vianett splits all incoming messages by space, and the first part goes to 'Prefix'.
    If you do not use prefixes, this can be very annoying!
    Set `False`: then, the whole message contents goes to 'body'.






Sending Parameters
==================

Provider-specific sending params: None






Additional Information
======================

OutgoingMessage.meta
--------------------
None.

IncomingMessage.meta
--------------------
* `prefix: str`: The first word in the message (keyword).
* `retrycount: int`: How many times the message has tried to be delivered.
* `operator: int`: The operator ID.
* `replypathid: int`: Only used for two-way dialogue, default 0.

MessageStatus.meta
------------------
... Tons of stupid, unpredictable fields






Receivers
=========

Source: /smsframework_vianett/receiver.py

Message Receiver: /im
---------------------
Go to Configuration > Connections, click 'Change'.
Put the message receiver URL into "HTTP url" field.

Message Receiver URL: `<provider-name>/im`

Status Receiver: /status
------------------------
Go to Configuration > Connections, click 'Change'.
Put the message receiver URL into "HTTP Status url" field.

Status Receiver URL: `<provider-name>/status`

