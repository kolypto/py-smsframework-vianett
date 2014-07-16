# -*- coding: utf-8 -*-

import urllib
import urllib2
from xml.etree import ElementTree

from datetime import datetime

from . import const


class VianettApiError(RuntimeError):
    """ Error reported by Vianett """
    def __init__(self, code, message):
        self.code = code
        super(VianettApiError, self).__init__(message)


class VianettHttpApi(object):
    """ Vianett HTTP API client """

    def __init__(self, user, password, https=False):
        """ Create an authenticated client

            :param user: Authentication: username
            :param password: Authentication: password
            :type https: bool
            :param https: Use HTTPS protocol for requests?
        """
        self._auth = dict(
            username=user,
            password=password
        )
        self._https = https

        #: Provider API endpoint
        self._hostname = 'smsc.vianett.no'

    def _api_request(self, method, **params):
        """ Make an API request and return the result

            :rtype: str
        """
        url = {
            'MT': '{schema}://{host}/V3/CPA/MT/MT.ashx',  # Outgoing message
        }[method]

        # Prepare the request
        url = url.format(
            schema='https' if self._https else 'http',
            host=self._hostname,
        )
        data = {}
        data.update(self._auth)
        data.update(params)
        post = urllib.urlencode(data)

        # Request
        req = urllib2.Request(url, post)
        res = urllib2.urlopen(req)
        return res.read()

    def api_request(self, method, **params):
        """ Make a custom request to Vianett and get the response object.

            This also handles errors reported by the Vianett API

            :type method: str
            :param method: Method name to call
            :param params: Method parameters to send
            :rtype: dict
            :raises HTTPError: Http error code
            :raises URLError: Connection failed
            :raises AssertionError: Invalid response
            :raises VianettApiError: Vianett error
        """
        response = self._api_request(method, **params)

        # Parse
        try:
            root = ElementTree.fromstring(response)
        except ElementTree.ParseError as e:
            raise AssertionError('Failed to parse response: {}: {}'.format(e.message, response))
        assert root.tag == 'ack', 'Invalid response: {}'.format(response)

        # Error?
        if root.attrib['errorcode'] != '200':
            raise VianettApiError(root.attrib['errorcode'], root.text)

        # Okay
        ret = root.attrib
        ret['text'] = root.text
        return ret

    def sendmsg(self, to, text, **params):
        """ Send SMS message

            See :meth:`VianettHttpApi.api_request` for the list of raised exceptions.

            :param to: Destination number, digits only
            :param text: Message text: str or unicode.
            :param params: Message parameters. See Vianett docs.

            :param msgid: Message reference id. Default: (generated)
            :param SenderAddress: Sender address: SenderID, or a phone number. Default: None
            :param SenderAddressType: MSISN=1, short code=2, alphanumeric=5
            :param Priority: 0 -- low priority, >0 -- high priority

            :rtype: str
            :returns: Message id
        """
        # Params
        params.update(
            tel=to,
            msg=text
        )

        # msgid
        if 'msgid' not in params:
            params['msgid'] = datetime.now().strftime('%Y%m%d%H%M%S')

        # Sender
        if 'SenderAddress' in params and params['SenderAddress'].lstrip('+').isdigit() == False:
            params['SenderAddressType'] = const.SenderAddressType.ALPHANUMERIC

        # Send it, response
        res = self.api_request('MT', **params)
        return res['refno']
