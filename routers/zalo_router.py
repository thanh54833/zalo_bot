from typing import Optional, Dict, Any, List

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Body, BackgroundTasks
from pydantic import BaseModel
from zlapi.Async import ZaloAPI
from zlapi.models import Message, ThreadType, MessageStyle, Mention, MultiMention

# Load environment variables
load_dotenv()

# Default cookie and IMEI values
DEFAULT_USERNAME = "0559362614"
DEFAULT_PASSWORD = "Lumia520"

DEFAULT_COOKIE = "zpw_sek=PHX8.442114449.a0.ztLU0MccDF3uXsxgIAOqy1A4KPjBd1Q40v4VY3sJ3PCpYMAK0j10g2FiK8aUcmdI5DqX-HRptY-RfsC4vyuqy0"
DEFAULT_IMEI = "2bd94c6b-f25c-418b-8e26-adb12c47086b-84fb6a68ab92a6d30981c69a1117885c"

# Create router
router = APIRouter(
    prefix="/api/zalo",
    tags=["zalo"],
    responses={404: {"description": "Not found"}},
)


# Models
class ZaloCredentials(BaseModel):
    username: str = DEFAULT_USERNAME
    password: str = DEFAULT_PASSWORD


class ZaloMessageRequest(BaseModel):
    recipient_id: str
    message: str
    thread_type: str = "USER"  # Default to user thread type
    style: Optional[Dict[str, Any]] = None
    mentions: Optional[List[Dict[str, Any]]] = None


class ZaloResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# Store client instances
zalo_clients = {}


# Helper function to get or create client
async def get_zalo_client(username: str):
    if username not in zalo_clients:
        raise HTTPException(status_code=401, detail="User not logged in")
    return zalo_clients[username]


# Custom ZaloAPI class for event handling
class CustomZaloAPI(ZaloAPI):
    """Custom ZaloAPI class for handling events"""

    def __init__(self, phone, password, imei, cookies, webhook_url=None):
        # Set auto_login to False to avoid automatic login during initialization
        super().__init__(phone, password, imei=imei, cookies=cookies, auto_login=False)
        self.webhook_url = webhook_url
        self.phone = phone
        self.password = password
        self._imei = imei  # Store imei for parent class methods

    async def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        """Handle incoming messages"""
        if self.webhook_url:
            import requests
            try:
                # Forward message to webhook
                requests.post(self.webhook_url, json={
                    "event_type": "message",
                    "data": {
                        "message_id": mid,
                        "author_id": author_id,
                        "message": message,
                        "thread_id": thread_id,
                        "thread_type": str(thread_type)
                    }
                })
            except Exception as e:
                print(f"Error forwarding message to webhook: {str(e)}")

    async def onEvent(self, event_data, event_type):
        """Handle incoming events"""
        if self.webhook_url:
            import requests
            try:
                # Forward event to webhook
                requests.post(self.webhook_url, json={
                    "event_type": "event",
                    "data": {
                        "event_data": str(event_data),
                        "event_type": str(event_type)
                    }
                })
            except Exception as e:
                print(f"Error forwarding event to webhook: {str(e)}")


# Routes
@router.post("/login", response_model=ZaloResponse)
async def login(credentials: ZaloCredentials):
    try:
        # Parse cookies from string if provided as a string
        cookies = {}
        if DEFAULT_COOKIE:
            # Parse cookie string into dictionary
            cookie_parts = DEFAULT_COOKIE.split(';')
            for part in cookie_parts:
                if '=' in part:
                    key, value = part.strip().split('=', 1)
                    cookies[key] = value

        if not cookies:
            return {
                "success": False,
                "message": "Login failed: This endpoint requires cookies for authentication as password login is not supported.",
                "data": None
            }

        # Create new client instance with proper parameters
        client = CustomZaloAPI(
            credentials.username,
            credentials.password,  # Not used for cookie login, but required by constructor
            imei=DEFAULT_IMEI,  # Use the default IMEI
            cookies=cookies
        )

        try:
            # Test if cookie is valid by fetching user info
            user_info = await client.fetchUserInfo(client.phone)

            if user_info:
                # Store client for later use
                zalo_clients[credentials.username] = client

                # Get session cookies for future use
                session_cookies = await client.getSession()

                return {
                    "success": True,
                    "message": "Login successful with cookies",
                    "data": {
                        "username": credentials.username,
                        "user_info": user_info,
                        "cookies": session_cookies,
                        "imei": DEFAULT_IMEI
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Login with cookie failed, invalid cookie or user not found.",
                    "data": None
                }
        except Exception as cookie_error:
            return {
                "success": False,
                "message": f"Login with cookie failed: {str(cookie_error)}",
                "data": {
                    "imei": DEFAULT_IMEI
                }
            }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "message": f"Error during login: {str(e)}",
            "data": {"traceback": traceback.format_exc()}
        }


@router.post("/logout", response_model=ZaloResponse)
async def logout(username: str = Body(..., embed=True)):
    if username in zalo_clients:
        client = zalo_clients[username]
        await client.logout()
        del zalo_clients[username]
        return {
            "success": True,
            "message": "Logout successful",
            "data": None
        }
    return {
        "success": False,
        "message": "User not logged in",
        "data": None
    }


@router.post("/send-message", response_model=ZaloResponse)
async def send_message(
        request: ZaloMessageRequest,
        background_tasks: BackgroundTasks,
        username: str = Body(..., embed=True)
):
    try:
        client = await get_zalo_client(username)

        # Determine thread type
        thread_type = ThreadType.USER if request.thread_type == "USER" else ThreadType.GROUP

        # Create message style if provided
        style = None
        if request.style:
            style = MessageStyle(
                offset=request.style.get("offset", 0),
                length=request.style.get("length", 1),
                style=request.style.get("style", "bold"),
                color=request.style.get("color", "ffffff"),
                size=request.style.get("size", "18")
            )

        # Create mentions if provided
        mention = None
        if request.mentions:
            mentions_list = []
            for m in request.mentions:
                mentions_list.append(
                    Mention(
                        uid=m.get("uid", ""),
                        length=m.get("length", 1),
                        offset=m.get("offset", 0),
                        auto_format=False
                    )
                )
            mention = MultiMention(mentions_list)

        # Create message
        message = Message(
            text=request.message,
            style=style,
            mention=mention
        )

        # Send message
        result = await client.sendMessage(
            message=message,
            thread_id=request.recipient_id,
            thread_type=thread_type
        )

        return {
            "success": True,
            "message": "Message sent successfully",
            "data": {"result": result}
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error sending message: {str(e)}",
            "data": None
        }


@router.get("/conversations", response_model=ZaloResponse)
async def get_conversations(username: str):
    try:
        client = await get_zalo_client(username)
        conversations = await client.fetchThreadList()

        return {
            "success": True,
            "message": "Conversations retrieved successfully",
            "data": {"conversations": conversations}
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving conversations: {str(e)}",
            "data": None
        }


@router.get("/messages/{thread_id}", response_model=ZaloResponse)
async def get_messages(thread_id: str, username: str):
    try:
        client = await get_zalo_client(username)
        messages = await client.fetchThreadMessages(thread_id=thread_id)

        return {
            "success": True,
            "message": "Messages retrieved successfully",
            "data": {"messages": messages}
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving messages: {str(e)}",
            "data": None
        }


@router.post("/mark-as-read", response_model=ZaloResponse)
async def mark_as_read(
        thread_id: str = Body(...),
        message_id: str = Body(...),
        client_message_id: str = Body(...),
        sender_id: str = Body(...),
        thread_type: str = Body(...),
        username: str = Body(...)
):
    try:
        client = await get_zalo_client(username)
        thread_type_enum = ThreadType.USER if thread_type == "USER" else ThreadType.GROUP

        await client.markAsRead(
            msgId=message_id,
            cliMsgId=client_message_id,
            senderId=sender_id,
            thread_id=thread_id,
            thread_type=thread_type_enum
        )

        return {
            "success": True,
            "message": "Message marked as read",
            "data": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error marking message as read: {str(e)}",
            "data": None
        }


@router.post("/start-listening", response_model=ZaloResponse)
async def start_listening(
        background_tasks: BackgroundTasks,
        username: str = Body(..., embed=True),
        webhook_url: str = Body(..., embed=True)
):
    try:
        # Parse cookies if needed
        parsed_cookies = {}
        if DEFAULT_COOKIE:
            # Use default cookie as last resort
            cookie_parts = DEFAULT_COOKIE.split(';')
            for part in cookie_parts:
                if '=' in part:
                    key, value = part.strip().split('=', 1)
                    parsed_cookies[key] = value

        # Check if client already exists
        if username in zalo_clients:
            client = zalo_clients[username]
            client.webhook_url = webhook_url
        else:
            # Create a new client with custom handler
            client = CustomZaloAPI(
                username,
                "",  # Password not needed when using cookies
                imei=DEFAULT_IMEI,  # Use the provided IMEI
                cookies=parsed_cookies,
                webhook_url=webhook_url
            )
            zalo_clients[username] = client

        # Start listening in background
        background_tasks.add_task(client.listen, reconnect=5)

        return {
            "success": True,
            "message": "Started listening for events",
            "data": {
                "username": username,
                "imei": DEFAULT_IMEI,
                "webhook_url": webhook_url
            }
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "message": f"Error starting listener: {str(e)}",
            "data": {"traceback": traceback.format_exc()}
        }
