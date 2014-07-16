from smsframework import IProvider, exc
from . import error
from .api import VianettHttpApi, VianettApiError
from urllib2 import URLError, HTTPError


class VianettProvider(IProvider):
    """ Vianett provider """

    def __init__(self, gateway, name, user, password, https=False, use_prefix=True):
        """ Configure Vianett provider

            :param user: Account username
            :param password: Account password
            :param https: Use HTTPS for outgoing messages?
            :param use_prefix: Do you use prefixes for incoming messages?
                    Stupidly, Vianett splits all incoming messages by space, and the first part goes to 'Prefix'.
                    If you do not use prefixes, this can be very annoying!
                    Set `False`: then, the whole message contents goes to 'body'
        """
        self.api = VianettHttpApi(user, password, https)
        self.use_prefix = use_prefix
        super(VianettProvider, self).__init__(gateway, name)

    def send(self, message):
        """ Send a message

            :type message: smsframework.data.OutgoingMessage.OutgoingMessage
            :rtype: OutgoingMessage
            """
        # Parameters
        params = {}
        if message.src:
            params['SenderAddress'] = message.src
        if message.provider_options.senderId:
            params['SenderAddress'] = message.provider_options.senderId
        if message.provider_options.escalate:
            params['Priority'] = 1
        if message.provider_options.allow_reply:
            params['ReplyPathValue'] = 60*24  # Should be enough?
        params.update(message.provider_params)

        # Send
        try:
            message.msgid = self.api.sendmsg(message.dst, message.body, **params)
            return message
        except AssertionError as e:
            raise exc.RequestError(e.message)
        except HTTPError as e:
            raise exc.MessageSendError(e.message)
        except URLError as e:
            raise exc.ConnectionError(e.message)
        except VianettApiError as e:
            raise error.VianettProviderError(e.code, e.message)

    def make_receiver_blueprint(self):
        """ Create the receiver blueprint """
        from . import receiver
        return receiver.bp

    # region Public

    def api_request(self, method, **params):
        """ Raw request to Vianett API

            :rtype: str
            :raises RequestError: Request error
            :raises ConnectionError: Connection error
            :raises MessageSendError: HTTP error
            :raises VianettProviderError: Error with the request
        """
        try:
            return self.api.api_request(method, **params)
        except AssertionError as e:
            raise exc.RequestError(e.message)
        except HTTPError as e:
            raise exc.MessageSendError(e.message)
        except URLError as e:
            raise exc.ConnectionError(e.message)
        except VianettApiError as e:
            raise error.VianettProviderError(e.code, e.message)

    #endregion
