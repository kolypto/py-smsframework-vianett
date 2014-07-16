#! /usr/bin/env python

from smsframework import Gateway
from smsframework_vianett import VianettProvider
from smsframework import OutgoingMessage

gateway = Gateway()
gateway.add_provider('vianett', VianettProvider,
    user='hakon@dignio.com',
    password='cn7xi',
    https=False
)

msg = OutgoingMessage('4797097418', 'Hello')
msg.provider_options.senderId = 'Dignio'
gateway.send(msg)
