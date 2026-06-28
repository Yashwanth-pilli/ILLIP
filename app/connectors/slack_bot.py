"""
Slack bot connector — optional, activates if SLACK_BOT_TOKEN + SLACK_APP_TOKEN are set.

Handles @mentions, DMs, and /illip slash command.
Uses Socket Mode (no public URL needed).
"""

import os
from app.utils import logger

_client = None
_socket_client = None
_running = False

_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", "")


async def _chat(user_input: str) -> str:
    try:
        from app.services.chat_service import ChatService
        svc = ChatService()
        reply = await svc.chat(user_input, stream=False)
        return reply if isinstance(reply, str) else str(reply)
    except Exception as e:
        return f"Error: {e}"


async def start_slack_bot():
    global _client, _socket_client, _running
    if not _BOT_TOKEN or not _APP_TOKEN:
        logger.info("Slack: SLACK_BOT_TOKEN or SLACK_APP_TOKEN not set, skipping")
        return
    try:
        from slack_sdk.web.async_client import AsyncWebClient  # type: ignore
        from slack_sdk.socket_mode.aiohttp import SocketModeClient  # type: ignore
        from slack_sdk.socket_mode.response import SocketModeResponse  # type: ignore
    except ImportError:
        logger.warning("Slack: slack_sdk not installed. pip install slack_sdk aiohttp")
        return

    _client = AsyncWebClient(token=_BOT_TOKEN)
    _socket_client = SocketModeClient(app_token=_APP_TOKEN, web_client=_client)

    async def handle(socket_client, req):
        if req.type == "events_api":
            payload = req.payload
            event = payload.get("event", {})
            etype = event.get("type", "")

            # Acknowledge immediately
            await socket_client.send_socket_mode_response(
                SocketModeResponse(envelope_id=req.envelope_id)
            )

            if etype in ("app_mention", "message") and not event.get("bot_id"):
                text = event.get("text", "").strip()
                # Strip bot mention prefix
                if "<@" in text:
                    text = text.split(">", 1)[-1].strip()
                if not text:
                    return
                channel = event.get("channel")
                reply = await _chat(text)
                try:
                    await _client.chat_postMessage(channel=channel, text=reply[:3000])
                except Exception as e:
                    logger.error(f"Slack send error: {e}")

        elif req.type == "slash_commands":
            payload = req.payload
            await socket_client.send_socket_mode_response(
                SocketModeResponse(envelope_id=req.envelope_id)
            )
            text = payload.get("text", "").strip()
            channel = payload.get("channel_id")
            if not text:
                await _client.chat_postMessage(channel=channel, text="Usage: `/illip <message>`")
                return
            reply = await _chat(text)
            try:
                await _client.chat_postMessage(channel=channel, text=reply[:3000])
            except Exception as e:
                logger.error(f"Slack slash command error: {e}")

    _socket_client.socket_mode_request_listeners.append(handle)
    _running = True
    try:
        await _socket_client.connect()
        logger.info("Slack bot connected via Socket Mode")
    except Exception as e:
        logger.error(f"Slack bot error: {e}")
        _running = False


async def stop_slack_bot():
    global _socket_client, _running
    if _socket_client:
        try:
            await _socket_client.disconnect()
        except Exception as e:
            logger.error(f"Slack stop error: {e}")
    _running = False
    _socket_client = None


from app.connectors.base_connector import BaseConnector  # noqa: E402


class SlackConnector(BaseConnector):
    name = "slack"
    description = "Slack bot — @mentions, DMs, /illip slash command via Socket Mode"
    required_env_vars = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN"]

    async def start(self) -> bool:
        await start_slack_bot()
        return _running

    async def stop(self) -> None:
        await stop_slack_bot()

    def is_active(self) -> bool:
        return _running
