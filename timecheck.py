#!/usr/bin/env python
import os, sys
from pytz import timezone
from datetime import datetime
from dateutil.parser import parse

def send_alert(mins):
    import smtplib
    from email.mime.text import MIMEText

    m= """
    Hi,

    This is a warning that your WeMo motion detector has not
    been triggered for %d minutes!

    UpAndAbout. 
    """ % int(mins)
    msg = MIMEText(m)

    me = "ross@servercode.co.uk"
    you = "wongwaikeong@gmail.com"
    msg['Subject'] = 'UpAndAbout warning!'
    msg['From'] = me
    msg['To'] = you

    s = smtplib.SMTP('localhost')
    s.sendmail(me, [you], msg.as_string())
    s.quit()


alert_time = 10
DATA = "/tmp/last_update.txt"

last = None
if not os.path.exists(DATA):
    print "Timestamp not yet generated"
    sys.exit(1)

last = open(DATA).read()
timestamp = parse(last.strip())

tz = timezone('Europe/London')
now = tz.localize(datetime.utcnow())

mins = float((now- timestamp).seconds / 60)
if mins > alert_time:
    send_alert(mins)
