import smtplib
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate


def read_email_info(filename):
    email_info = dict()
    lines = {"send_from", "send_to", "server", "port", "login", "password"}

    with open(filename, "r", encoding="utf-8") as email_info_file:
        for line in email_info_file:
            key, value = line.replace("\n", "").split(":", 1)
            email_info[key] = value

    if set(email_info.keys()) != lines:
        raise Exception("Not all the email parameters are in the {} file".format(filename))

    return email_info


def send_mail(send_from, send_to, subject, text, files=None,
              server="smtp.mail.ru", port=465, login="theormechipmm@mail.ru", password="UEBQFbkoeG3hpM"):
    assert isinstance(send_to, list)

    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(text))

    for f in files or []:
        with open(f, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=basename(f)
            )
        # After the file is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
        msg.attach(part)


    smtp_server = smtplib.SMTP_SSL(server, port)
    smtp_server.login(login, password)
    smtp_server.sendmail(send_from, send_to, msg.as_string())
    smtp_server.close()