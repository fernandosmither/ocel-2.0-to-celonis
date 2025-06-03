import asyncio
import httpx
import json
import re
import logging
from dotenv import load_dotenv
import os
from typing import Callable, Optional, Awaitable

from cloudflare.client import R2Client

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Keeping hardcoded global constants as requested
BASE_LOGIN_URL = "https://id.celonis.cloud"

TYPE_MAP = {
    "string": "CT_UTF8_STRING",
    "integer": "CT_LONG",
    "datetime": "CT_INSTANT",
    "float": "CT_DOUBLE",
    "boolean": "CT_BOOLEAN",
}

CATEGORIES = [
    {
        "metadata": {"name": "Processes", "namespace": "celonis"},
        "values": [
            {
                "name": "curriculum",
                "displayName": "curriculum",
                "namespace": "custom",
                "description": "",
            }
        ],
    }
]


class CelonisClient:
    """Client for interacting with Celonis API."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        log_callback: Optional[Callable[[str, str], Awaitable[None]]] = None,
    ):
        """Initialize the Celonis client.

        Args:
            base_url: Celonis academic alliance base URL (e.g., "https://academic-example.eu-2.celonis.cloud")
            username: Celonis username
            password: Celonis password
            log_callback: Optional async callback function for forwarding log messages.
                         Should accept (level, message) where level is "info" or "warning"
        """
        self.client = httpx.AsyncClient(follow_redirects=False, timeout=30.0)
        self.csrf_token = None
        self.base_url = base_url.rstrip("/")  # Remove trailing slash if present
        self.username = username
        self.password = password
        self.log_callback = log_callback

        # Construct endpoints using the provided base URL
        self.obj_endpoint = (
            f"{self.base_url}/bl/api/v1/types/objects?environment=develop"
        )
        self.evt_endpoint = (
            f"{self.base_url}/bl/api/v1/types/events?environment=develop"
        )

    async def _log_info(self, message: str):
        """Log an info message and forward via callback if available."""
        logger.info(message)
        if self.log_callback:
            await self.log_callback("info", message)

    async def _log_warning(self, message: str):
        """Log a warning message and forward via callback if available."""
        logger.warning(message)
        if self.log_callback:
            await self.log_callback("warning", message)

    async def _get_csrf_token(self):
        """Initialize session and get CSRF token."""
        await self.client.get(f"{BASE_LOGIN_URL}", follow_redirects=True)

        response = await self.client.get(
            f"{BASE_LOGIN_URL}/user/", follow_redirects=True
        )

        self.csrf_token = self.client.cookies.get("XSRF-TOKEN")

        if not self.csrf_token:
            # Try to extract from response content if not in cookies
            match = re.search(r'name="_csrf" value="([^"]+)"', response.text)
            if match:
                self.csrf_token = match.group(1)
            else:
                logger.error("Failed to extract CSRF token")
                return False

        return True

    async def handle_mfa(self, response, mfa_code: str):
        """Handle MFA authentication with provided code.

        Args:
            response: The HTTP response that triggered MFA
            mfa_code: The MFA code to submit

        Returns:
            bool: True if MFA was successful, False otherwise
        """
        await self._log_info("Processing MFA authentication.")

        # Update CSRF token from response cookies if available
        if "XSRF-TOKEN" in self.client.cookies:
            self.csrf_token = self.client.cookies.get("XSRF-TOKEN") or self.csrf_token

        # Get MFA page to prepare for code entry
        mfa_url = f"{BASE_LOGIN_URL}{response.headers.get('Location')}"
        await self.client.get(mfa_url, follow_redirects=True)

        # Submit MFA code
        mfa_data = {"_csrf": self.csrf_token, "one-time-password": mfa_code}
        mfa_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": BASE_LOGIN_URL,
            "Referer": mfa_url,
        }

        # Now enable follow_redirects for the MFA submission
        mfa_response = await self.client.post(
            f"{BASE_LOGIN_URL}/user/api/login/mfa",
            data=mfa_data,
            headers=mfa_headers,
            follow_redirects=True,
        )

        logger.info(f"MFA Response Status Code: {mfa_response.status_code}")
        if mfa_response.status_code == 200:
            await self._log_info("MFA authentication successful.")
            return True
        else:
            logger.error("MFA authentication failed.")
            return False

    async def login(self) -> httpx.Response:
        """Authenticate with Celonis.

        Returns:
            httpx.Response: The login response
        """
        if not self.username or not self.password:
            raise ValueError("Username and password must be provided")

        if not await self._get_csrf_token():
            raise Exception("Failed to get CSRF token")

        login_data = {
            "_csrf": self.csrf_token,
            "username": self.username,
            "password": self.password,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": BASE_LOGIN_URL,
            "Referer": f"{BASE_LOGIN_URL}/user/ui/login",
        }

        response = await self.client.post(
            f"{BASE_LOGIN_URL}/user/api/login", data=login_data, headers=headers
        )

        return response

    async def get_celonis_cloud_token(self):
        """Get the Celonis Cloud tokens in the client session"""

        await self.client.get(self.base_url, follow_redirects=True)

        for cookie in self.client.cookies.jar:
            logger.debug(f"Cookie: {cookie}")

        xsrf_token = (
            self.client.cookies.get("XSRF-TOKEN", domain=self.base_url.split("://")[-1])
            or self.csrf_token
        )

        if xsrf_token:
            self.client.headers.update({"X-Xsrf-Token": xsrf_token})

    async def download_jsonocel_from_r2(self, file_uuid: str) -> dict:
        """Download and parse a jsonocel file from R2 using UUID.

        Args:
            file_uuid: UUID of the file in R2

        Returns:
            dict: Parsed jsonocel data

        Raises:
            Exception: If download or parsing fails
        """
        try:
            await self._log_info(f"Downloading jsonocel from R2 with UUID: {file_uuid}")

            r2_client = R2Client()
            file_content = await r2_client.download_file(file_uuid)

            await self._log_info("Download complete, parsing JSON...")
            data = json.loads(file_content.decode("utf-8"))

            await self._log_info("Jsonocel file parsed successfully")
            return data

        except Exception as e:
            await self._log_warning(f"Failed to download/parse jsonocel: {str(e)}")
            raise

    async def download_jsonocel(self, identifier: str) -> dict:
        """Download and parse a jsonocel file from R2 using UUID.

        Args:
            identifier: UUID of the file in R2

        Returns:
            dict: Parsed jsonocel data

        Raises:
            Exception: If download or parsing fails
        """
        return await self.download_jsonocel_from_r2(identifier)

    async def _sanitize_name(self, raw: str) -> str:
        """Sanitize a name to ensure it's valid for Celonis.

        Args:
            raw: The raw name string

        Returns:
            str: The sanitized name
        """
        chars = []
        # ensure starts with letter
        if not raw or not raw[0].isalpha():
            chars.append("A")
            await self._log_warning(f"Name '{raw}' invalid start; prepending 'A'")
        for c in raw:
            if c.isalnum():
                chars.append(c)
            else:
                await self._log_warning(f"Stripping invalid '{c}' from '{raw}'")
        return "".join(chars)

    async def _sanitize_fields(self, fields: list[dict]) -> list[dict]:
        """Sanitize field names in a list of field dictionaries.

        Args:
            fields: List of field dictionaries

        Returns:
            list[dict]: Sanitized fields
        """
        out = []
        for f in fields:
            name = f["name"]
            if not name or not name[0].isalpha():
                name = "A" + name
                await self._log_warning(f"Field name invalid start; became '{name}'")
            cleaned = "".join(ch for ch in name if ch.isalnum())
            if cleaned != name:
                await self._log_warning(f"Sanitized field name '{name}' → '{cleaned}'")
            f["name"] = cleaned
            out.append(f)
        return out

    async def _create_types(
        self,
        items: list[dict],
        endpoint: str,
        require_time: bool,
        include_color: bool,
    ):
        """Create types (object or event) in Celonis.

        Args:
            items: List of type definitions
            endpoint: API endpoint for type creation
            require_time: Whether to ensure Time field exists
            include_color: Whether to include color in the payload
        """
        for it in items:
            name = await self._sanitize_name(it["name"])

            fields = [
                {
                    "name": a["name"],
                    "namespace": "custom",
                    "dataType": TYPE_MAP[a["type"]],
                }
                for a in it["attributes"]
            ]
            # ensure ID
            if not any(f["name"] == "ID" for f in fields):
                fields.append(
                    {"name": "ID", "namespace": "custom", "dataType": "CT_UTF8_STRING"}
                )
            # for events, ensure Time
            if require_time and not any(f["name"] == "Time" for f in fields):
                fields.append(
                    {"name": "Time", "namespace": "custom", "dataType": "CT_INSTANT"}
                )
            fields = await self._sanitize_fields(fields)

            payload = {
                "name": name,
                "tags": [],
                "description": "",
                "fields": fields,
                "relationships": [],
                "categories": CATEGORIES,
            }
            if include_color:
                payload["color"] = "#4608B3"

            resp = await self.client.post(endpoint, json=payload)
            try:
                resp.raise_for_status()
                await self._log_info(
                    f"✓ Created {endpoint.split('/')[-1][:-1]} type '{name}'"
                )
            except httpx.HTTPStatusError as e:
                body = resp.json()
                if (
                    resp.status_code == 400
                    and body.get("errors", [{}])[0].get("errorCode") == "ALREADY_EXISTS"
                ):
                    await self._log_warning(f"'{name}' already exists; skipping")
                else:
                    import traceback

                    traceback.print_exc()
                    raise e

    async def create_object_types(self, object_types: list[dict]):
        """Create object types in Celonis.

        Args:
            object_types: List of object type definitions
        """
        await self._create_types(
            object_types, self.obj_endpoint, require_time=False, include_color=True
        )

    async def create_event_types(self, event_types: list[dict]):
        """Create event types in Celonis.

        Args:
            event_types: List of event type definitions
        """
        await self._create_types(
            event_types, self.evt_endpoint, require_time=True, include_color=False
        )

    async def close(self):
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()


async def main():
    """Main function to demonstrate usage of the CelonisClient."""
    username = os.getenv("CELONIS_USERNAME")
    password = os.getenv("CELONIS_PASSWORD")
    base_url = os.getenv("CELONIS_BASE_URL")
    assert username is not None
    assert password is not None
    assert base_url is not None

    client = CelonisClient(base_url=base_url, username=username, password=password)

    try:
        response = await client.login()

        if (
            response.status_code == 303
            and "/user/ui/login/mfa" in response.headers.get("Location", "")
        ):
            mfa_code = input("Please enter your MFA code: ")
            if not await client.handle_mfa(response, mfa_code):
                await client.close()
                raise Exception("MFA authentication failed")

        await client.get_celonis_cloud_token()

        with open("data.jsonocel", encoding="utf-8") as f:
            data = json.load(f)

        await client.create_object_types(data["objectTypes"])
        await client.create_event_types(data["eventTypes"])

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
