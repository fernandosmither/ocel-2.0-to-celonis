import asyncio
import httpx
import json
import re
import logging
from dotenv import load_dotenv
import os
from typing import Callable, Optional, Awaitable

from cloudflare.client import R2Client
from splitter.client import splitter

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
                        Should accept (level, message) where level is "info", "warning" or "error"
        """
        self.client = httpx.AsyncClient(
            follow_redirects=False,
            timeout=60.0,
            # verify=False,
            # proxy="http://localhost:8080",
        )
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
        self.factory_create_endpoint = f"{self.base_url}/bl/api/v1/factories/sql?environment=develop&useV2Manifest=true"
        self.factory_update_endpoint_base = f"{self.base_url}/bl/api/v1/factories/sql"

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

    async def _log_error(self, message: str):
        """Log an error message and forward via callback if available."""
        logger.error(message)
        if self.log_callback:
            await self.log_callback("error", message)

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

        await self.get_session_and_pac4j_token()

    async def get_session_and_pac4j_token(self):
        """Get the session and pac4j token in the client session"""
        url = f"{self.base_url}/api/public/authentication/status"
        await self.client.get(url, follow_redirects=True)
        url = f"{self.base_url}/api/auth-handler/commence?redirect=%2Fui%2F"
        await self.client.get(url, follow_redirects=True)
        xsrf_token = self.client.cookies.get(
            "XSRF-TOKEN", domain=self.base_url.split("://")[-1]
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
            data: dict = json.loads(file_content.decode("utf-8"))

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
        """
        • Keep only [0-9a-zA-Z ].
        • Capital-case each word.
        • Remove all spaces.
        • Guarantee the first character is a letter
        (prepend "A" if the cleaned string starts with a digit or is empty).
        """
        if raw is None:
            raw = ""

        allowed = []
        for ch in raw:
            if ch.isalnum() or ch == " ":
                allowed.append(ch)
            else:
                await self._log_warning(f"Stripping invalid '{ch}' from '{raw}'")

        cleaned = "".join(allowed)

        cleaned = " ".join(word.capitalize() for word in cleaned.split())
        cleaned = cleaned.replace(" ", "")  # remove remaining spaces

        if not cleaned or not cleaned[0].isalpha():
            await self._log_warning(f"Name '{raw}' invalid start; prepending 'A'")
            cleaned = "A" + cleaned

        return cleaned

    async def _sanitize_fields(self, fields: list[dict]) -> list[dict]:
        """
        Uses the same rules as _sanitize_name to sanitize fields.
        """
        sanitized_fields: list[dict] = []

        for field in fields:
            original_name = field.get("name") or ""
            new_name = await self._sanitize_name(original_name)

            if new_name != original_name:
                await self._log_warning(
                    f"Sanitized field name '{original_name}' → '{new_name}'"
                )

            field["name"] = new_name
            sanitized_fields.append(field)

        return sanitized_fields

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
            id_time_fields = [f for f in fields if f["name"] in ["ID", "Time"]]
            other_fields = [f for f in fields if f["name"] not in ["ID", "Time"]]

            sanitized_fields = await self._sanitize_fields(other_fields)

            fields = sanitized_fields + id_time_fields

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

            resp = await self.client.post(endpoint, json=payload, timeout=300)
            try:
                logger.info(resp.json())
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

    async def _process_single_sql_chunk(
        self,
        type_name: str,
        sql_chunk: str,
        chunk_idx: int,
        total_chunks: int,
        target_kind: str,
        data_connection_id: str,
    ):
        """Process a single SQL chunk by creating and updating a factory.

        Args:
            type_name: Name of the object/event type
            sql_chunk: SQL chunk to process
            chunk_idx: Index of this chunk (1-based)
            total_chunks: Total number of chunks
            target_kind: "OBJECT" or "EVENT"
            data_connection_id: Data connection ID (empty for objects, UUID for events)
        """
        await self._log_info(
            f"Processing chunk {chunk_idx}/{total_chunks} for '{type_name}'"
        )

        try:
            create_payload = {
                "factoryId": "00000000-0000-0000-0000-000000000000",
                "namespace": "custom",
                "changeDate": 0,
                "creationDate": 0,
                "dataConnectionId": data_connection_id,
                "displayName": f"{type_name} - {chunk_idx}",
                "target": {
                    "entityRef": {"name": type_name, "namespace": "custom"},
                    "kind": target_kind,
                },
                "draft": True,
                "localParameters": [],
                "changedBy": {},
                "createdBy": {},
            }

            create_response = await self.client.post(
                self.factory_create_endpoint,
                json=create_payload,
                timeout=300,
            )
            create_response.raise_for_status()

            factory_data = create_response.json()
            factory_id = factory_data["factoryId"]

            await self._log_info(
                f"✓ Created factory {factory_id} for '{type_name}' chunk {chunk_idx}"
            )

            update_endpoint = f"{self.factory_update_endpoint_base}/{factory_id}?environment=develop&useV2Manifest=true"

            property_names = ["ID"]
            if target_kind == "EVENT":
                property_names.append("Time")
                import re

                column_matches = re.findall(r'AS\s+"([^"]+)"', sql_chunk, re.IGNORECASE)
                if column_matches:
                    # Remove duplicates while preserving order, skip ID and Time as they're already added
                    seen = {"ID", "Time"}
                    for col in column_matches:
                        if col not in seen:
                            property_names.append(col)
                            seen.add(col)

            update_payload = factory_data.copy()
            update_payload.update(
                {
                    "transformations": [
                        {
                            "namespace": "custom",
                            "foreignKeyNames": [],
                            "propertyNames": property_names,
                            "propertySqlFactoryDatasets": [
                                {
                                    "id": f"{type_name}Attributes",
                                    "disabled": False,
                                    "sql": sql_chunk,
                                    "overwrite": None,
                                    "materialiseCte": False,
                                    "type": "SQL_FACTORY_DATA_SET",
                                    "completeOverwrite": False,
                                }
                            ],
                            "changeSqlFactoryDatasets": [],
                            "relationshipTransformations": [],
                        }
                    ],
                    "draft": False,
                    "saveMode": "VALIDATE",
                    "disabled": True,
                }
            )

            update_response = await self.client.put(
                update_endpoint, json=update_payload, timeout=300
            )
            update_response.raise_for_status()

            await self._log_info(
                f"✓ Successfully updated factory with SQL for '{type_name}' chunk {chunk_idx}"
            )

        except httpx.HTTPStatusError as e:
            if "update_response" in locals() and update_response.status_code == 400:
                try:
                    error_body = update_response.json()
                    if error_body.get("statusCode") == 400:
                        error_message = error_body.get(
                            "message", "Unknown update error"
                        )
                        await self._log_error(
                            f"Update error for '{type_name}' chunk {chunk_idx}: {error_message}"
                        )
                        return
                except (json.JSONDecodeError, KeyError):
                    pass

            import traceback

            traceback.print_exc()
            raise e

    async def _process_single_sql_chunk_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        type_name: str,
        sql_chunk: str,
        chunk_idx: int,
        total_chunks: int,
        target_kind: str,
        data_connection_id: str,
    ):
        """Process a single SQL chunk with semaphore to limit concurrency.

        Args:
            semaphore: Semaphore to limit concurrent operations
            type_name: Name of the object/event type
            sql_chunk: SQL chunk to process
            chunk_idx: Index of this chunk (1-based)
            total_chunks: Total number of chunks
            target_kind: "OBJECT" or "EVENT"
            data_connection_id: Data connection ID (empty for objects, UUID for events)
        """
        async with semaphore:
            await self._process_single_sql_chunk(
                type_name,
                sql_chunk,
                chunk_idx,
                total_chunks,
                target_kind,
                data_connection_id,
            )

    async def _create_factory_transformation(
        self,
        type_name: str,
        sql_chunks: list[str],
        target_kind: str,
        semaphore: asyncio.Semaphore,
        data_connection_id: str = "",
    ):
        """Create factory transformations for a single type (object or event).

        Args:
            type_name: Name of the object/event type
            sql_chunks: List of SQL chunks for this type
            target_kind: "OBJECT" or "EVENT"
            data_connection_id: Data connection ID (empty for objects, UUID for events)
        """

        await self._log_info(
            f"Processing {target_kind.lower()} type '{type_name}' with {len(sql_chunks)} chunks in parallel"
        )

        # Create tasks for all SQL chunks with semaphore
        chunk_tasks = []
        for chunk_idx, sql_chunk in enumerate(sql_chunks, 1):
            task = self._process_single_sql_chunk_with_semaphore(
                semaphore,
                type_name,
                sql_chunk,
                chunk_idx,
                len(sql_chunks),
                target_kind,
                data_connection_id,
            )
            chunk_tasks.append(task)

        # Run all chunks with limited concurrency
        if chunk_tasks:
            chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)

            # Check for and log any failures
            failed_chunks = []
            for i, result in enumerate(chunk_results):
                if isinstance(result, Exception):
                    failed_chunks.append(i + 1)  # 1-based chunk index
                    await self._log_error(
                        f"Chunk {i + 1} failed for '{type_name}': {str(result)}"
                    )

            if failed_chunks:
                await self._log_error(
                    f"Failed chunks for '{type_name}': {failed_chunks}"
                )
            else:
                await self._log_info(
                    f"✓ Successfully processed all {len(sql_chunks)} chunks for '{type_name}'"
                )

    async def create_transformations(self, data: dict):
        """Create both object and event transformations in Celonis using the splitter.

        Args:
            data: OCEL object data to be split and processed
        """
        await self._log_info("Starting transformations creation process...")

        try:
            objects_sql, events_sql, relationships_sql, object_relationships_sql = (
                splitter.split(data)
            )
        except Exception as e:
            await self._log_error(f"Error splitting data: {str(e)}")
            import traceback

            traceback.print_exc()
            raise

        total_types = len(objects_sql) + len(events_sql)
        await self._log_info(
            f"Split data into {len(objects_sql)} object types and {len(events_sql)} event types. "
            f"There are {len(relationships_sql)} event-object relationships to process."
        )

        max_concurrent_chunks = 8  # Limit to 8 parallel chunk operations
        semaphore = asyncio.Semaphore(max_concurrent_chunks)

        # Create all object transformation tasks
        object_tasks = []
        for object_type_name, sql_chunks in objects_sql.items():
            task = self._create_factory_transformation(
                object_type_name,
                sql_chunks,
                "OBJECT",
                semaphore,
                "",  # Empty data connection ID for objects
            )
            object_tasks.append(task)

        # Create all event transformation tasks
        event_tasks = []
        for event_type_name, sql_chunks in events_sql.items():
            task = self._create_factory_transformation(
                event_type_name,
                sql_chunks,
                "EVENT",
                semaphore,
                "00000000-0000-0000-0000-000000000000",  # UUID for events
            )
            event_tasks.append(task)

        # Run all object transformations in parallel
        if object_tasks:
            await self._log_info(
                f"Running {len(object_tasks)} object transformations in parallel..."
            )
            object_results = await asyncio.gather(*object_tasks, return_exceptions=True)

            # Check for and log any failures
            for i, result in enumerate(object_results):
                if isinstance(result, Exception):
                    object_name = list(objects_sql.keys())[
                        i
                    ]  # Get the object name for the failed task
                    await self._log_error(
                        f"Object transformation failed for '{object_name}': {str(result)}"
                    )

        # Run all event transformations in parallel
        if event_tasks:
            await self._log_info(
                f"Running {len(event_tasks)} event transformations in parallel..."
            )
            event_results = await asyncio.gather(*event_tasks, return_exceptions=True)

            # Check for and log any failures
            for i, result in enumerate(event_results):
                if isinstance(result, Exception):
                    event_name = list(events_sql.keys())[
                        i
                    ]  # Get the event name for the failed task
                    await self._log_error(
                        f"Event transformation failed for '{event_name}': {str(result)}"
                    )

        await self._log_info(f"✓ Completed transformations for all {total_types} types")

        await self._create_event_object_relationships(relationships_sql, semaphore)

        await self._log_info("✓ Completed relationships")

    async def _fetch_all_events(self) -> list[dict]:
        """Fetch all events from Celonis API with pagination.

        Returns:
            list[dict]: List of all events
        """
        all_events = []
        page_number = 0

        while True:
            endpoint = f"{self.base_url}/bl/api/v1/types/events?requestMode=ALL&environment=develop&pageNumber={page_number}"

            try:
                response = await self.client.get(endpoint)
                response.raise_for_status()

                data = response.json()
                events = data.get("content", [])
                all_events.extend(events)

                await self._log_info(
                    f"Fetched page {page_number + 1} with {len(events)} events"
                )

                if data.get("last", True):
                    break

                page_number += 1

            except Exception as e:
                await self._log_error(
                    f"Error fetching events page {page_number}: {str(e)}"
                )
                raise

        await self._log_info(f"Fetched total of {len(all_events)} events")
        return all_events

    async def _add_relationship_to_event(
        self, event: dict, obj_names: list[str], evt_name: str
    ) -> list[str]:
        """Add 1:n relationships to an event and update it via API.

        Args:
            event: The event object from Celonis API
            obj_names: List of object names to create relationships with
            evt_name: Original event name for logging

        Returns:
            List of object names for which new relationships were added
        """
        updated_event = event.copy()

        for attr in [
            "creationDate",
            "createdBy",
            "changedBy",
            "id",
            "namespace",
        ]:
            updated_event.pop(attr, None)

        if "relationships" not in updated_event:
            updated_event["relationships"] = []

        new_relationships_added = []
        for obj_name in obj_names:
            relationship_exists = any(
                rel.get("name") == obj_name
                and rel.get("target", {}).get("objectRef", {}).get("name") == obj_name
                for rel in updated_event["relationships"]
            )

            if not relationship_exists:
                new_relationship = {
                    "cardinality": "HAS_MANY",
                    "name": obj_name,
                    "namespace": "custom",
                    "target": {
                        "mappedBy": None,
                        "mappedByNamespace": None,
                        "objectRef": {"name": obj_name, "namespace": "custom"},
                    },
                }
                updated_event["relationships"].append(new_relationship)
                new_relationships_added.append(obj_name)
            else:
                await self._log_info(
                    f"Relationship {evt_name} -> {obj_name} already exists, skipping"
                )

        if new_relationships_added:
            event_id = event["id"]
            update_endpoint = (
                f"{self.base_url}/bl/api/v1/types/events/{event_id}?environment=develop"
            )

            response = await self.client.put(
                update_endpoint, json=updated_event, timeout=300
            )
            response.raise_for_status()

            relationships_str = ", ".join(new_relationships_added)
            await self._log_info(
                f"✓ Added 1:N relationships for {evt_name} -> [{relationships_str}]"
            )
        else:
            await self._log_info(f"No new relationships to add for event {evt_name}")

        return new_relationships_added

    async def _process_single_event_relationships_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        evt_key: str,
        rel_data: dict,
        event_lookup: dict,
    ):
        """Process relationships for a single event with semaphore to limit concurrency.

        Args:
            semaphore: Semaphore to limit concurrent operations
            evt_key: Event key (lowercase)
            rel_data: Relationship data for this event
            event_lookup: Lookup dictionary for events
        """
        async with semaphore:
            try:
                evt_name = rel_data["original_evt_name"]
                obj_names = rel_data["objects"]
                obj_sql_map = rel_data["obj_sql_map"]

                event = event_lookup.get(evt_key)
                if not event:
                    await self._log_error(f"Event '{evt_name}' not found")
                    return

                new_relationships_added = await self._add_relationship_to_event(
                    event, obj_names, evt_name
                )

                if new_relationships_added:
                    new_obj_sql_map = {
                        obj: obj_sql_map[obj] for obj in new_relationships_added
                    }
                    await self._create_relationship_factory_and_transformations(
                        evt_name, new_obj_sql_map
                    )

            except Exception as e:
                await self._log_error(
                    f"Error processing relationships for event {evt_name}: {str(e)}"
                )
                import traceback

                traceback.print_exc()

    async def _create_relationship_factory_and_transformations(
        self, evt_name: str, event_obj_sql_map: dict[str, list[str]]
    ):
        """Create factory and transformations for event-object relationships.

        Args:
            evt_name: Event name
            event_obj_sql_map: Dictionary mapping object names to their SQL chunks
        """
        try:
            await self._log_info(
                f"Creating factory for event '{evt_name}' relationships"
            )

            create_payload = {
                "factoryId": "00000000-0000-0000-0000-000000000000",
                "namespace": "custom",
                "changeDate": 0,
                "creationDate": 0,
                "dataConnectionId": "00000000-0000-0000-0000-000000000000",
                "displayName": evt_name,
                "target": {
                    "entityRef": {"name": evt_name, "namespace": "custom"},
                    "kind": "EVENT",
                },
                "draft": True,
                "localParameters": [],
                "changedBy": {},
                "createdBy": {},
            }

            create_response = await self.client.post(
                self.factory_create_endpoint,
                json=create_payload,
                timeout=300,
            )
            create_response.raise_for_status()

            factory_data = create_response.json()
            factory_id = factory_data["factoryId"]

            await self._log_info(
                f"✓ Created relationship factory {factory_id} for '{evt_name}'"
            )

            relationship_transformations = []

            existing_transformations = factory_data.get("transformations", [{}])[0].get(
                "relationshipTransformations", []
            )

            for rel_transform in existing_transformations:
                relationship_name = rel_transform.get("relationshipName")
                if relationship_name in event_obj_sql_map:
                    sql_chunks = event_obj_sql_map[relationship_name]
                    sql_factory_datasets = []

                    for chunk_idx, sql_chunk in enumerate(sql_chunks, 1):
                        chunk_id = f"{relationship_name.lower()}{chunk_idx}"
                        sql_factory_datasets.append(
                            {
                                "id": chunk_id,
                                "disabled": False,
                                "sql": sql_chunk,
                                "overwrite": None,
                                "materialiseCte": False,
                                "type": "SQL_FACTORY_DATA_SET",
                                "completeOverwrite": False,
                            }
                        )

                    relationship_transformations.append(
                        {
                            "relationshipName": relationship_name,
                            "sqlFactoryDatasets": sql_factory_datasets,
                        }
                    )

                    await self._log_info(
                        f"✓ Added {len(sql_chunks)} SQL chunks for {evt_name} -> {relationship_name}"
                    )
                else:
                    relationship_transformations.append(
                        {
                            "relationshipName": relationship_name,
                            "sqlFactoryDatasets": [],
                        }
                    )

            update_endpoint = f"{self.factory_update_endpoint_base}/{factory_id}?environment=develop&useV2Manifest=true"

            update_payload = factory_data.copy()
            update_payload.update(
                {
                    "transformations": [
                        {
                            "namespace": "custom",
                            "foreignKeyNames": [],
                            "propertyNames": ["ID", "Time"],
                            "propertySqlFactoryDatasets": [],
                            "changeSqlFactoryDatasets": [],
                            "relationshipTransformations": relationship_transformations,
                        }
                    ],
                    "draft": False,
                    "saveMode": "VALIDATE",
                    "disabled": True,
                    "factoryValidationStatus": "NOT_VALIDATED",
                }
            )

            update_response = await self.client.put(
                update_endpoint, json=update_payload, timeout=300
            )
            update_response.raise_for_status()

            factory_validation_status = update_response.json()[
                "factoryValidationStatus"
            ]
            if factory_validation_status == "VALID":
                await self._log_info(
                    f"✓ Successfully created transformations for event '{evt_name}'"
                )
            else:
                await self._log_error(
                    f"Error creating transformations for event '{evt_name}': {factory_validation_status}"
                )

        except Exception as e:
            await self._log_error(
                f"Error creating factory/transformations for event {evt_name}: {str(e)}"
            )
            import traceback

            traceback.print_exc()

    async def _create_event_object_relationships(
        self, relationships_sql: dict[str, list[str]], semaphore: asyncio.Semaphore
    ):
        """Create 1:n relationships between events and objects, and their transformations.

        Args:
            relationships_sql: Dictionary with keys formatted as "{evt_name}_{obj_name}_relations"
                             and values as lists of SQL chunks
            semaphore: Semaphore to limit concurrent operations
        """
        if not relationships_sql:
            await self._log_info("No relationships to process")
            return

        await self._log_info(
            f"Processing {len(relationships_sql)} event-object relationships and transformations in parallel"
        )

        all_events = await self._fetch_all_events()

        event_lookup = {}
        for event in all_events:
            event_name = event.get("name", "").lower()
            event_lookup[event_name] = event

        event_relationships = {}

        for relationship_key, sql_chunks in relationships_sql.items():
            try:
                # Parse the key: "{evt_name}_{obj_name}_relations"
                if not relationship_key.endswith("_relations"):
                    await self._log_error(
                        f"Invalid relationship key format: {relationship_key}"
                    )
                    continue

                name_part = relationship_key[:-10]  # Remove "_relations"
                parts = name_part.rsplit("_", 1)

                if len(parts) != 2:
                    await self._log_error(
                        f"Could not parse event and object names from: {relationship_key}"
                    )
                    continue

                evt_name, obj_name = parts

                evt_key = evt_name.lower()
                if evt_key not in event_relationships:
                    event_relationships[evt_key] = {
                        "original_evt_name": evt_name,
                        "objects": [],
                        "obj_sql_map": {},
                    }
                event_relationships[evt_key]["objects"].append(obj_name)
                event_relationships[evt_key]["obj_sql_map"][obj_name] = sql_chunks

            except Exception as e:
                await self._log_error(
                    f"Error parsing relationship {relationship_key}: {str(e)}"
                )
                continue

        # Create tasks for all events with relationships
        event_tasks = []
        for evt_key, rel_data in event_relationships.items():
            task = self._process_single_event_relationships_with_semaphore(
                semaphore, evt_key, rel_data, event_lookup
            )
            event_tasks.append(task)

        # Run all events in parallel with limited concurrency
        if event_tasks:
            await self._log_info(
                f"Running {len(event_tasks)} event relationship tasks in parallel..."
            )
            event_results = await asyncio.gather(*event_tasks, return_exceptions=True)

            # Check for and log any failures
            failed_events = []
            for i, result in enumerate(event_results):
                if isinstance(result, Exception):
                    evt_key = list(event_relationships.keys())[i]
                    evt_name = event_relationships[evt_key]["original_evt_name"]
                    failed_events.append(evt_name)
                    await self._log_error(
                        f"Event relationship processing failed for '{evt_name}': {str(result)}"
                    )

            if failed_events:
                await self._log_error(f"Failed event relationships: {failed_events}")

        await self._log_info(
            "✓ Completed processing all event-object relationships and transformations"
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
        await client.create_transformations(data)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
