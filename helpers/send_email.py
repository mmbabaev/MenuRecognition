#!/usr/bin/env python
# -*- coding: utf-8 -*-

import smtplib
import json
import smtplib
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate


def send_mail(msg, send_to):
    send_from = "recognizermenu"
    password = "SuperSecret1"

    msg['From'] = send_from
    msg['Date'] = formatdate(localtime=True)

    server = smtplib.SMTP('smtp.gmail.com:587')
    server.ehlo()
    server.starttls()
    server.login(send_from, password)
    server.sendmail(send_from, send_to, msg.as_string())
    server.close()


def send_mail_files(files, send_to):
    msg = MIMEMultipart()
    msg['To'] = send_to
    msg['Subject'] = "Выгрузка json меню"

    for f in files or []:
        with open(f, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=basename(f)
            )
        # After the file is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
        msg.attach(part)

    send_mail(msg, send_to)


def send_mail_message(subject, message, send_to):
    message = message.encode('utf-8')

    msg = MIMEText(message)
    msg['To'] = send_to
    msg['Subject'] = subject

    send_mail(msg, send_to)

