from datetime import datetime, timedelta

from flask import Blueprint
from flask.globals import request, g

from smsframework.data import IncomingMessage
from smsframework.data import MessageAccepted, MessageDelivered, MessageExpired, MessageError

bp = Blueprint('smsframework-vianett', __name__, url_prefix='/')


@bp.route('/im')
def im():
    """ Incoming message handler

        * sourceaddr: The originator number.
        * destinationaddr: The destination number.
        * prefix: The first word in the message (keyword).
        * message: The last part of the message.
        * refno: ViaNett's message ID. Reference number.
        * retrycount: How many times the message has tried to be delivered.
        * operator: The operator ID. 1 is Telenor Mobile (Norway), 2 is NetCom (Norway), etc.
        * requesttype: This field will have the value "mo" on incoming messages.
        * username: Optional username.
        * password: Optional password.
        * replypathid: Only used for two-way dialogue, default 0.
    """
    req = request.args.to_dict()

    # Check
    for n in ('sourceaddr', 'message', 'refno', 'destinationaddr', 'prefix', 'retrycount', 'operator', 'replypathid'):
        assert n in req, 'Vianett message with missing "{}" field: {}'.format(n, req)

    # Prefixes
    if not g.provider.use_prefix:
        req['message'] = ' '.join(filter(lambda x: x, (req['prefix'], req['message'])))
        req['prefix'] = ''

    # IncomingMessage
    message = IncomingMessage(
        src=req['sourceaddr'],
        body=req['message'],
        msgid=req['refno'],
        dst=req['destinationaddr'],
        rtime=datetime.utcnow(),
        meta = {
            'prefix': req['prefix'],
            'retrycount': req['retrycount'],
            'operator': req['operator'],
            'replypathid': req['replypathid']
        }
    )

    # Process it
    " :type: smsframework.IProvider.IProvider "
    g.provider._receive_message(message)  # any exceptions will respond with 500, and Vianett will happily retry later

    # Ack
    return '<ack refno="{msgid}" errorcode="0" />'.format(msgid=message.msgid)


@bp.route('/status')
def status():
    """ Incoming status report

        * refno: msgid
        * now: Datetime in CET: "06.10.2005 11:24:07" (not always provided)
        * requesttype: type of status report:

            'mtstatus': Delivered to the terminal
                Simple delivery report from operator:
                    * errorcode: '0' if delivered fine
                    * msgok: Whether the message was successfully submitted. (not always provided)
                        'True' -- yes, '-1' -- pending

                Advanced delivery report from operator:
                    * SentDate: Datetime in CET when the message was sent: "06.10.2005 11:24:07"
                    * ErrorCode: error code. '200' is ok
                    * ErrorDescription: error description string
                    * Status: (mysterious status text)
                    * Msg: (even more mysterious status text)
                    * CPACost, CPARevenue, NetPrice, ConsumerPrice: message price
                    * ... more stupid fields

            'notificationstatus': Sent to phone
                * Status:
                    'ACCEPTD' or 'BUFFERD' -- queued
                    'DELIVRD' -- delivered to the terminal
                * StatusDescription: Description of the 'Status' field (not always provided)
                * StatusCode: Code representing the status of the message
    """
    req = request.args.to_dict()

    def _check_fields(*fields):
        for n in fields:
            assert n in req, 'Vianett status with missing "{}" field: {}'.format(n, req)

    _check_fields('requesttype')
    if req['requesttype'] == 'notificationstatus':
        _check_fields('Status', 'StatusDescription', 'StatusCode')

        # Create status
        status = {
            'DELIVRD': MessageDelivered,
            'ACCEPTD': MessageAccepted,
            'BUFFERD': MessageAccepted
        }[req['Status']](req['refno'], meta=req)
        status.status_code = req['StatusCode']
        status.status = '{0[Status]}: {0[StatusDescription]}'.format(req)
    elif req['requesttype'] == 'mtstatus':
        if 'ErrorCode' in req:
            _check_fields('ErrorCode', 'ErrorDescription', 'Status', 'Msg')

            # Create status
            status = {
                True: MessageDelivered,
                False: MessageError
            }[req['ErrorCode'] == '200'](req['refno'], meta=req)
            status.status_code = req['ErrorCode']
            status.status = '{0[ErrorDescription]}: {0[Status]}: {0[Msg]}'.format(req)
        else:
            _check_fields('errorcode')

            # Simple
            status = {
                True: MessageDelivered,
                False: MessageError
            }[req['errorcode'] == '0'](req['refno'], meta=req)
            status.status_code = req['errorcode']
            status.status = '{} and {}'.format(req['errorcode'], req['msgok'] if 'msgok' in req else '?')
    else:
        raise AssertionError('Vianett status with an unsupported `requesttype`: {}'.format(req))

    # Process it
    g.provider._receive_status(status)  # exception respond with http 500

    # Ack
    return '<?xml version="1.0"?><ack refno="1234" errorcode="0" />'
