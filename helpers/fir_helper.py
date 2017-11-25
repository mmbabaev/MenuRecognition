#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Send to single device.
from pyfcm import FCMNotification
from config import FIREBASE_API_KEY
from helpers.send_email import send_mail_message

push_service = FCMNotification(api_key=FIREBASE_API_KEY)


def notify_user(user_to, user_from, rest, access):
    token = user_to.fir_token
    title = rest.name

    from_name = user_from.last_name + " " + user_from.name

    if access:
        message = u"Вы получили доступ к ресторану от пользователя " + from_name
    else:
        message = u"Вы больше не можете редактировать ресторан " + title


    send_push(token, title, message)
    send_mail_message(title, message, user_to.email)


def send_push(registration_id, title, message):
    if registration_id is None or registration_id == "":
        return

    result = push_service.notify_single_device(registration_id=registration_id, message_title=title,
                                               message_body=message)
    print(result)
    return result["success"]

