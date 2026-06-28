"""
Email connector — SMTP send + IMAP receive polling.

Config (env vars):
  EMAIL_ADDRESS    — the ILLIP email address
  EMAIL_PASSWORD   — app password
  SMTP_HOST        — default: smtp.gmail.com
  SMTP_PORT        — default: 587
  IMAP_HOST        — default: imap.gmail.com
  IMAP_PORT        — default: 993

Inbound emails → ILLIP chat → reply via SMTP.
Polls every 5 minutes. Only activates if EMAIL_ADDRESS is set.
"""

import asyncio
import imaplib
import email as email_lib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.utils import logger

_EMAIL = os.getenv("EMAIL_ADDRESS", "")
_PASS = os.getenv("EMAIL_PASSWORD", "")
_SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
_SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
_IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
_IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
_POLL_INTERVAL = 300  # 5 min

_running = False
_poll_task = None


async def send_email(to: str, subject: str, body: str) -> bool:
    """Send email via SMTP. Returns True on success."""
    if not _EMAIL or not _PASS:
        logger.warning("Email: credentials not configured")
        return False
    try:
        import aiosmtplib  # type: ignore
        msg = MIMEMultipart()
        msg["From"] = _EMAIL
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        await aiosmtplib.send(
            msg,
            hostname=_SMTP_HOST,
            port=_SMTP_PORT,
            username=_EMAIL,
            password=_PASS,
            start_tls=True,
        )
        logger.info(f"Email sent to {to}")
        return True
    except ImportError:
        logger.warning("Email: aiosmtplib not installed. pip install aiosmtplib")
        return False
    except Exception as e:
        logger.error(f"Email send error: {e}")
        return False


def _fetch_unread() -> list[dict]:
    """Blocking IMAP fetch — run in executor."""
    results = []
    try:
        conn = imaplib.IMAP4_SSL(_IMAP_HOST, _IMAP_PORT)
        conn.login(_EMAIL, _PASS)
        conn.select("INBOX")
        _, data = conn.search(None, "UNSEEN")
        ids = data[0].split()
        for eid in ids[-10:]:  # max 10 unread per poll
            _, msg_data = conn.fetch(eid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)
            sender = msg.get("From", "")
            subject = msg.get("Subject", "(no subject)")
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="replace")
            results.append({"from": sender, "subject": subject, "body": body[:2000]})
        conn.logout()
    except Exception as e:
        logger.error(f"IMAP fetch error: {e}")
    return results


async def _poll_loop():
    while _running:
        try:
            loop = asyncio.get_event_loop()
            emails = await loop.run_in_executor(None, _fetch_unread)
            for em in emails:
                try:
                    from app.services.chat_service import ChatService
                    svc = ChatService()
                    prompt = f"Email from {em['from']}\nSubject: {em['subject']}\n\n{em['body']}"
                    reply = await svc.chat(prompt, stream=False)
                    reply_text = reply if isinstance(reply, str) else str(reply)
                    # Extract sender address
                    sender_addr = em["from"]
                    if "<" in sender_addr:
                        sender_addr = sender_addr.split("<")[1].rstrip(">")
                    await send_email(
                        to=sender_addr,
                        subject=f"Re: {em['subject']}",
                        body=reply_text,
                    )
                except Exception as e:
                    logger.error(f"Email process error: {e}")
        except Exception as e:
            logger.error(f"Email poll error: {e}")
        await asyncio.sleep(_POLL_INTERVAL)


async def start_email_connector():
    global _running, _poll_task
    if not _EMAIL:
        logger.info("Email: EMAIL_ADDRESS not set, skipping")
        return
    _running = True
    _poll_task = asyncio.create_task(_poll_loop())
    logger.info(f"Email connector started (polling {_IMAP_HOST} every {_POLL_INTERVAL}s)")


async def stop_email_connector():
    global _running, _poll_task
    _running = False
    if _poll_task:
        _poll_task.cancel()
        try:
            await _poll_task
        except asyncio.CancelledError:
            pass
        _poll_task = None


from app.connectors.base_connector import BaseConnector  # noqa: E402


class EmailConnector(BaseConnector):
    name = "email"
    description = "Email connector — SMTP send + IMAP receive, auto-replies via ILLIP"
    required_env_vars = ["EMAIL_ADDRESS", "EMAIL_PASSWORD"]
    optional_env_vars = ["SMTP_HOST", "SMTP_PORT", "IMAP_HOST", "IMAP_PORT"]

    async def start(self) -> bool:
        await start_email_connector()
        return _running

    async def stop(self) -> None:
        await stop_email_connector()

    def is_active(self) -> bool:
        return _running
