import asyncio
import json
import time
import uuid
from typing import Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from .client import CelonisClient
from enums import ClientCommand, ServerResponse


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, dict] = {}
        self.session_timeout = 300

    def create_session(self, session_id: str) -> dict:
        """Create a new session with CelonisClient and metadata."""
        session = {
            "client": None,
            "last_activity": time.time(),
            "websocket": None,
            "mfa_response": None,
        }
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session and update last activity."""
        if session_id in self.sessions:
            self.sessions[session_id]["last_activity"] = time.time()
            return self.sessions[session_id]
        return None

    async def cleanup_session(self, session_id: str):
        """Clean up a specific session."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            if session["client"]:
                await session["client"].close()
            del self.sessions[session_id]

    async def cleanup_expired_sessions(self):
        """Clean up sessions that have exceeded the timeout."""
        current_time = time.time()
        expired_sessions = []

        for session_id, session in self.sessions.items():
            if current_time - session["last_activity"] > self.session_timeout:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            await self.cleanup_session(session_id)


session_manager = SessionManager()


async def cleanup_task():
    """Background task to clean up expired sessions."""
    while True:
        await asyncio.sleep(60)  # Check every minute
        await session_manager.cleanup_expired_sessions()


async def send_response(
    websocket: WebSocket, response_type: ServerResponse, data: dict | None = None
):
    """Send a response to the WebSocket client."""
    message = {"type": response_type.value}
    if data:
        message.update(data)

    if websocket.client_state == WebSocketState.CONNECTED:
        await websocket.send_text(json.dumps(message))


def create_log_callback(websocket: WebSocket):
    """Create a log callback function for forwarding log messages via websocket.

    Args:
        websocket: The WebSocket connection to forward messages to

    Returns:
        A callback function that accepts (level, message) and forwards them
    """

    async def log_callback(level: str, message: str):
        """Forward log message via websocket."""
        await send_response(
            websocket, ServerResponse.LOG_MESSAGE, {"level": level, "message": message}
        )

    return log_callback


router = APIRouter(prefix="/celonis", tags=["celonis"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    session_id = str(uuid.uuid4())

    session = session_manager.create_session(session_id)
    session["websocket"] = websocket

    await send_response(
        websocket,
        ServerResponse.CONNECTED,
        {
            "session_id": session_id,
            "message": f"Connected with session ID: {session_id}",
        },
    )

    try:
        while True:
            data = await websocket.receive_text()

            try:
                command_data = json.loads(data)
                command = command_data.get("command")

                if not command:
                    await send_response(
                        websocket,
                        ServerResponse.ERROR,
                        {"message": "Command field is required"},
                    )
                    continue

                if command == ClientCommand.START_LOGIN:
                    await handle_start_login(websocket, session, command_data)

                elif command == ClientCommand.SUBMIT_MFA_CODE:
                    await handle_submit_mfa(websocket, session, command_data)

                elif command == ClientCommand.DOWNLOAD_AND_CREATE_TYPES:
                    await handle_download_and_create_types(
                        websocket, session, command_data
                    )

                elif command == ClientCommand.RETRY_LOGIN:
                    await handle_retry_login(websocket, session, command_data)

                elif command == ClientCommand.RETRY_MFA:
                    await handle_retry_mfa(websocket, session, command_data)

                elif command == ClientCommand.CLOSE:
                    await handle_close(websocket, session)
                    break

                else:
                    await send_response(
                        websocket,
                        ServerResponse.ERROR,
                        {"message": f"Unknown command: {command}"},
                    )

            except json.JSONDecodeError:
                await send_response(
                    websocket,
                    ServerResponse.ERROR,
                    {"message": "Invalid JSON format"},
                )
            except Exception as e:
                await send_response(
                    websocket,
                    ServerResponse.ERROR,
                    {"message": f"Unexpected error: {str(e)}"},
                )

    except WebSocketDisconnect:
        pass
    finally:
        await session_manager.cleanup_session(session_id)


async def handle_start_login(websocket: WebSocket, session: dict, command_data: dict):
    """Handle start_login command."""
    base_url = command_data.get("base_url")
    username = command_data.get("username")
    password = command_data.get("password")

    if not base_url or not username or not password:
        await send_response(
            websocket,
            ServerResponse.ERROR,
            {"message": "Base URL, username and password are required"},
        )
        return

    try:
        if session["client"]:
            await session["client"].close()

        # Create log callback for this session's websocket
        log_callback = create_log_callback(websocket)
        session["client"] = CelonisClient(base_url, username, password, log_callback)

        response = await session["client"].login()

        if (
            response.status_code == 303
            and "/user/ui/login/mfa" in response.headers.get("Location", "")
        ):
            session["mfa_response"] = response
            await send_response(websocket, ServerResponse.MFA_REQUIRED)
        elif response.status_code == 200:
            await session["client"].get_celonis_cloud_token()
            await send_response(websocket, ServerResponse.LOGIN_SUCCESS)
        else:
            await send_response(
                websocket,
                ServerResponse.LOGIN_FAILED,
                {"message": f"Login failed with status {response.status_code}"},
            )

    except Exception as e:
        await send_response(
            websocket, ServerResponse.ERROR, {"message": f"Login error: {str(e)}"}
        )


async def handle_submit_mfa(websocket: WebSocket, session: dict, command_data: dict):
    """Handle submit_mfa_code command."""
    mfa_code = command_data.get("code")

    if not mfa_code:
        await send_response(
            websocket, ServerResponse.ERROR, {"message": "MFA code is required"}
        )
        return

    if not session["client"] or not session["mfa_response"]:
        await send_response(
            websocket,
            ServerResponse.ERROR,
            {"message": "No active MFA session. Please start login first."},
        )
        return

    client: CelonisClient = session["client"]

    try:
        success = await client.handle_mfa(session["mfa_response"], mfa_code)

        if success:
            await client.get_celonis_cloud_token()
            session["mfa_response"] = None
            await send_response(websocket, ServerResponse.MFA_SUCCESS)
        else:
            await send_response(
                websocket,
                ServerResponse.MFA_FAILED,
                {"message": "Invalid MFA code"},
            )

    except Exception as e:
        await send_response(
            websocket, ServerResponse.ERROR, {"message": f"MFA error: {str(e)}"}
        )


async def handle_download_and_create_types(
    websocket: WebSocket, session: dict, command_data: dict
):
    """Handle download_and_create_types command."""
    uuid = command_data.get("uuid")

    if not uuid:
        await send_response(
            websocket, ServerResponse.ERROR, {"message": "UUID is required"}
        )
        return

    if not session["client"]:
        await send_response(
            websocket,
            ServerResponse.ERROR,
            {"message": "No active client session. Please login first."},
        )
        return

    client: CelonisClient = session["client"]

    try:
        await send_response(websocket, ServerResponse.DOWNLOAD_STARTED)
        data = await client.download_jsonocel(uuid)
        await send_response(websocket, ServerResponse.DOWNLOAD_COMPLETE)

        await send_response(websocket, ServerResponse.TYPES_CREATION_STARTED)

        if "objectTypes" in data:
            await client.create_object_types(data["objectTypes"])

        if "eventTypes" in data:
            await client.create_event_types(data["eventTypes"])

        await client.create_transformations(data)

        await send_response(websocket, ServerResponse.TYPES_CREATION_COMPLETE)

    except Exception as e:
        await send_response(
            websocket,
            ServerResponse.ERROR,
            {"message": f"Processing error: {str(e)}"},
        )


async def handle_retry_login(websocket: WebSocket, session: dict, command_data: dict):
    """Handle retry_login command."""
    await handle_start_login(websocket, session, command_data)


async def handle_retry_mfa(websocket: WebSocket, session: dict, command_data: dict):
    """Handle retry_mfa command."""
    await handle_submit_mfa(websocket, session, command_data)


async def handle_close(websocket: WebSocket, session: dict):
    """Handle close command."""
    if session["client"]:
        await session["client"].close()
        session["client"] = None

    await send_response(websocket, ServerResponse.CLOSED)


__all__ = ["router", "session_manager", "cleanup_task"]
