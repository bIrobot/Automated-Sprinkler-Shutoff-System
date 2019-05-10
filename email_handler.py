#!/usr/bin/env python

import imaplib
import logging
import random
import smtplib
import ssl
import string
import time
from email.message import EmailMessage
from email.parser import BytesParser
from itertools import chain


class emailHandler():

    def __init__(self, server, port, user, password):
        self.server = server
        self.port = port
        self.user = user
        self.password = password

        # Restrict mail search
        self.criteria = {'FROM': 'developer2334@gmail.com'}

        # connect to server
        logging.debug('connecting to ' + self.server)

        server = imaplib.IMAP4_SSL(self.server, self.port)
        server.login(self.user, self.password)
        server.select('INBOX')

        result, data = server.uid('search', None, self.search_string(self.criteria))

        result, data = server.uid('search', None, 'ALL')
        for uid in data[0].split():
            server.uid('store', uid, '+FLAGS', '\\Deleted')
        server.expunge()

        server.logout()

    def get_email(self):
        email_recieved = False
        disabled_time = 0

        # Have to login/logout each time because that's the only way to get fresh results.
        server = imaplib.IMAP4_SSL(self.server, self.port)
        server.login(self.user, self.password)
        server.select('INBOX')

        result, data = server.uid('search', None, self.search_string(self.criteria))

        msg = 0
        uids = data[0].split()
        if uids:
            result, data = server.uid('fetch', max(uids), '(RFC822)')  # fetch entire message

            msg = BytesParser().parsebytes(data[0][1])

            print('New message :::::::::::::::::::::')
            print('To: %s' % msg['to'])
            print('From: %s' % msg['from'])
            print('Subject: %s' % msg['subject'])
            print(self.get_first_text_block(msg))

            result, data = server.uid('search', None, 'ALL')
            for uid in data[0].split():
                server.uid('store', uid, '+FLAGS', '\\Deleted')
            server.expunge()

            try:
                if (msg['subject'].split()[1].lower() == 'enable'):
                    disabled_time = 0
                    email_recieved = True
                elif (msg['subject'].split()[1].lower() == 'disable'):
                    if (msg['subject'].split()[3].lower() == 'hour' or msg['subject'].split()[3].lower() == 'hours'):
                        disabled_time = float(msg['subject'].split()[2]) * 3600
                        email_recieved = True
                    elif (msg['subject'].split()[3].lower() == 'day' or msg['subject'].split()[3].lower() == 'days'):
                        disabled_time = float(
                            msg['subject'].split()[2]) * 86400
                        email_recieved = True
                else:
                    self.send_email(msg['from'])
            except:
                self.send_email(msg['from'])

        server.close()
        server.logout()

        return email_recieved, disabled_time

    def send_email(self, address):
        message = EmailMessage()
        message["Subject"] = "Usage"
        message["From"] = self.user
        message["To"] = address
        message.set_content("""\
        Usage: sprinkler {enable | disable} <time> {hour(s) | day(s)}

        Examples:
        sprinkler disable 3.5 hours
        sprinkler enable
        """)

        # Send the message via our own SMTP server.
        s = smtplib.SMTP_SSL(self.server)
        s.send_message(message)
        s.quit()

    def search_string(self, criteria):
        c = list(
            map(lambda t: (t[0], '"' + str(t[1]) + '"'), criteria.items()))
        return '(%s)' % ' '.join(chain(*c))
        # Produce search string in IMAP format:
        #   e.g. (FROM "me@gmail.com" SUBJECT "abcde" BODY "123456789")

    def get_first_text_block(self, msg):
        type = msg.get_content_maintype()

        if type == 'multipart':
            for part in msg.get_payload():
                if part.get_content_maintype() == 'text':
                    return part.get_payload()
        elif type == 'text':
            return msg.get_payload()
