# -*- coding: utf-8 -*-

import unittest
from datetime import datetime

from flask import Flask
from freezegun import freeze_time

from smsframework import Gateway, OutgoingMessage
from smsframework.providers import NullProvider
from smsframework_vianett import VianettProvider

from smsframework_vianett import error


class VianettProviderTest(unittest.TestCase):
    def setUp(self):
        # Gateway
        gw = self.gw = Gateway()
        gw.add_provider('null', NullProvider)  # provocation
        gw.add_provider('main', VianettProvider, user='kolypto', password='1234')

        # Flask
        app = self.app = Flask(__name__)

        # Register receivers
        gw.receiver_blueprints_register(app, prefix='/a/b/')

    def _mock_response(self, refno, errorcode, text):
        """ Monkey-patch VianettHttpApi so it returns a predefined response """
        def _api_request(method, **params):
            return '<?xml version="1.0"?><ack refno="{}" errorcode="{}">{}</ack>'.format(refno, errorcode, text)
        self.gw.get_provider('main').api._api_request = _api_request

    def test_blueprints(self):
        """ Test blueprints """
        self.assertEqual(
            self.gw.receiver_blueprints().keys(),
            ['main']
        )

    def test_api_request(self):
        """ Test raw requests """
        provider = self.gw.get_provider('main')

        # OK
        self._mock_response(1, '200', 'OK')
        self.assertEqual(provider.api_request('MT'), {'refno': '1', 'errorcode': '200', 'text': 'OK'})

        # Error reported
        self._mock_response(2, '400', 'Fail')
        self.assertRaises(error.VianettProviderError, provider.api_request, 'MT')

    def test_send(self):
        """ Test message send """
        gw = self.gw

        # OK
        self._mock_response(11111111, '200', 'OK')
        message = gw.send(OutgoingMessage('+123456', 'hey', provider='main'))
        self.assertEqual(message.msgid, '11111111')

        # Failure
        self._mock_response(22222222, '400', 'FAIL')
        self.assertRaises(error.VianettProviderError, gw.send, OutgoingMessage('+123456', 'hey', provider='main'))

    @freeze_time('2014-07-01 12:00:00')
    def test_receive_message(self):
        """ Test message receipt """

        # Message receiver
        messages = []
        def receiver(message):
            messages.append(message)
        self.gw.onReceive += receiver

        with self.app.test_client() as c:
            res = c.get('/a/b/main/im'
                        '?refno=19194091'
                        '&now=20140623122057'
                        '&requesttype=mo'
                        '&sourceaddr=47580008000626'
                        '&destinationaddr=4794041334'
                        '&replypathid=0'
                        '&prefix=TEST'
                        '&message=Hi,%20man'
                        '&retrycount=0'
                        '&operator=435'
                        '&referenceid='
                        '&username='
                        '&password=')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(messages), 1)
            message = messages.pop()
            self.assertEqual(message.provider, 'main')
            self.assertEqual(message.msgid, '19194091')
            self.assertEqual(message.src, '47580008000626')
            self.assertEqual(message.dst, '4794041334')
            self.assertEqual(message.body, 'Hi, man')
            self.assertEqual(message.rtime.isoformat(), '2014-07-01T12:00:00')
            self.assertEqual(message.meta, {'operator': '435', 'prefix': 'TEST', 'replypathid': '0', 'retrycount': '0'})

    @freeze_time('2014-07-01 12:00:00')
    def test_receive_status(self):
        """ Test status receipt """

        # TODO: this test only contains data from the documentation. It's probably wrong! test with real data instead

        # Status receiver
        statuses = []

        def receiver(status):
            statuses.append(status)

        self.gw.onStatus += receiver

        with self.app.test_client() as c:
            # Status 1: notificationstatus, ACCEPTD
            res = c.get('/a/b/main/status'
                        '?password='
                        '&username='
                        '&refno=1234'
                        '&Status=ACCEPTD'
                        '&requesttype=notificationstatus'
                        '&StatusDescription=Absent+subscriber'
                        '&StatusCode=107'
                        '&now=06%2E10%2E2005+11%3A24%3A07&')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(statuses), 1)
            st = statuses.pop()
            self.assertEqual(st.msgid, '1234')
            self.assertEqual(st.rtime.isoformat(), '2014-07-01T12:00:00')
            self.assertTrue('now' in st.meta)  # everything copied
            self.assertEqual(st.provider, 'main')
            self.assertEqual(st.accepted, True)
            self.assertEqual(st.delivered, False)
            self.assertEqual(st.expired, False)
            self.assertEqual(st.status_code, '107')
            self.assertEqual(st.status, 'ACCEPTD: Absent subscriber')
            self.assertEqual(st.error, False)

            # Status 2: notificationstatus, DELIVRD
            res = c.get('/a/b/main/status'
                        '?password='
                        '&username='
                        '&refno=1234'
                        '&Status=DELIVRD'
                        '&requesttype=notificationstatus'
                        '&StatusDescription='
                        '&StatusCode=0'
                        '&now=05%2E10%2E2005+00%3A30%3A06&')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(statuses), 1)
            st = statuses.pop()
            self.assertEqual(st.msgid, '1234')
            self.assertEqual(st.rtime.isoformat(), '2014-07-01T12:00:00')
            self.assertTrue('now' in st.meta)  # everything copied
            self.assertEqual(st.provider, 'main')
            self.assertEqual(st.accepted, True)
            self.assertEqual(st.delivered, True)
            self.assertEqual(st.expired, False)
            self.assertEqual(st.status_code, '0')
            self.assertEqual(st.status, 'DELIVRD: ')
            self.assertEqual(st.error, False)

            # Status 3: Simple delivery report from operator:
            res = c.get('/a/b/main/status'
                        '?password='
                        '&username='
                        '&refno=1'
                        '&requesttype=mtstatus'
                        '&msgok=-1'
                        '&errorcode=0'
                        '&now=05%2E10%2E2005+03%3A04%3A57&')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(statuses), 1)
            st = statuses.pop()
            self.assertEqual(st.msgid, '1')
            self.assertEqual(st.rtime.isoformat(), '2014-07-01T12:00:00')
            self.assertTrue('now' in st.meta)  # everything copied
            self.assertEqual(st.provider, 'main')
            self.assertEqual(st.accepted, True)
            self.assertEqual(st.delivered, True)
            self.assertEqual(st.expired, False)
            self.assertEqual(st.status_code, '0')
            self.assertEqual(st.status, '0 and -1')
            self.assertEqual(st.error, False)


            # Status 4: Advanced delivery report from operator
            res = c.get('/a/b/main/status'
                        '?password='
                        '&username='
                        '&refno=1234'
                        '&requesttype=mtstatus'
                        '&msgok=True'
                        '&ErrorDescription=OK'
                        '&ErrorCode=200'
                        '&Status='
                        '&SentDate=05%2E10%2E2005+00%3A41%3A27'
                        '&OperatorID=1'
                        '&CountryID=1'
                        '&CampaignID=1234'
                        '&Cut=90&CPAContentCost=0'
                        '&CPACost=0'
                        '&CPARevenue=1%2C35'
                        '&NetPrice=1%2C5'
                        '&ConsumerPrice=3'
                        '&PriceGroup=300'
                        '&Msg=Your message is accepted%2E'
                        '&Tel=1234'
                        '&FromAlpha=vianett'
                        '&sno=1963'
                        '&now=05%2E10%2E2005+00%3A41%3A43&')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(statuses), 1)
            st = statuses.pop()
            self.assertEqual(st.msgid, '1234')
            self.assertEqual(st.rtime.isoformat(), '2014-07-01T12:00:00')
            self.assertTrue('now' in st.meta)  # everything copied
            self.assertEqual(st.provider, 'main')
            self.assertEqual(st.accepted, True)
            self.assertEqual(st.delivered, True)
            self.assertEqual(st.expired, False)
            self.assertEqual(st.status_code, '200')
            self.assertEqual(st.status, 'OK: : Your message is accepted.')
            self.assertEqual(st.error, False)
