"""Check your Gmail IMAP (incoming) and SMTP (outgoing) settings WITHOUT starting the website.

    cd backend
    python check_mail.py                      # tests IMAP login + SMTP login
    python check_mail.py --send-test a@b.com  # also sends one small test e-mail to that address

Every line says OK or FAILED with the reason, so you know exactly what to fix in backend/.env.
"""
import imaplib
import smtplib
import sys
from email.message import EmailMessage

from app.config import settings
from app.services import mailnet


def check_imap() -> bool:
    print("\n--- IMAP (incoming mail -> website) ---")
    if not (settings.IMAP_HOST and settings.IMAP_USER and settings.IMAP_PASSWORD):
        print("FAILED : IMAP_HOST / IMAP_USER / IMAP_PASSWORD are not all set in backend/.env")
        return False
    try:
        conn = mailnet.connect_imap()
        conn.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
        typ, data = conn.select(settings.IMAP_FOLDER, readonly=True)
        if typ != "OK":
            print(f"FAILED : cannot open folder '{settings.IMAP_FOLDER}'")
            return False
        print(f"OK     : connected using {mailnet.LAST_TLS}")
        print(f"OK     : logged in as {settings.IMAP_USER}; folder '{settings.IMAP_FOLDER}' has {data[0].decode()} messages")
        conn.logout()
        print(f"INFO   : mail sent TO {settings.IMAP_USER} from a DIFFERENT address will appear on the website")
        return True
    except imaplib.IMAP4.error as exc:
        print(f"FAILED : login rejected ({str(exc)[:120]}). Use a Gmail App Password and make sure IMAP is enabled in Gmail settings.")
    except Exception as exc:
        print(f"FAILED : could not reach {settings.IMAP_HOST}:{settings.IMAP_PORT} ({type(exc).__name__})")
    return False


def check_smtp(send_to: str = "") -> bool:
    print("\n--- SMTP (your replies -> customer) ---")
    if not (settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD):
        print("FAILED : SMTP_HOST / SMTP_USER / SMTP_PASSWORD are not all set in backend/.env")
        return False
    if not settings.SEND_REPLIES_VIA_SMTP:
        print("WARNING: SEND_REPLIES_VIA_SMTP=false, replies would only be recorded, not e-mailed")
    try:
        with mailnet.open_smtp() as smtp:
            print(f"OK     : connected using {mailnet.LAST_TLS}")
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            print(f"OK     : logged in as {settings.SMTP_USER}")
            if send_to:
                msg = EmailMessage()
                msg["From"], msg["To"], msg["Subject"] = settings.SMTP_USER, send_to, "MailNexa test e-mail"
                msg.set_content("If you can read this, replies from the website will reach customers.")
                smtp.send_message(msg)
                print(f"OK     : test e-mail sent to {send_to}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("FAILED : login rejected. Use a Gmail App Password (not your normal password).")
    except Exception as exc:
        print(f"FAILED : {type(exc).__name__}: {str(exc)[:120]}")
    return False


if __name__ == "__main__":
    target = sys.argv[sys.argv.index("--send-test") + 1] if "--send-test" in sys.argv[:-1] else ""
    ok_imap, ok_smtp = check_imap(), check_smtp(target)
    print("\nRESULT :", "all good - start the backend and test with a real mail" if ok_imap and ok_smtp else "fix the FAILED lines above, then run this again")
    sys.exit(0 if ok_imap and ok_smtp else 1)
