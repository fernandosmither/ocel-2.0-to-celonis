#!/usr/bin/env python3
"""
Test client for the Celonis WebSocket API.
This demonstrates the full flow: upload file to R2, then process via WebSocket.
"""

import asyncio
import json
import websockets
import os
import httpx
from dotenv import load_dotenv

load_dotenv()


async def test_websocket_client():
    """Test the WebSocket API with the new R2 upload flow."""

    # Step 0: Upload file to R2 (if user provides a file path)
    file_path = input(
        "Enter path to your .jsonocel file (or press Enter to skip upload): "
    ).strip()

    if file_path and os.path.exists(file_path):
        print(f"Uploading {file_path} to R2...")

        # Upload file to get UUID
        with open(file_path, "rb") as f:
            files = {"file": f}
            upload_response = httpx.post(
                "http://localhost:8000/cloudflare/upload", files=files
            )

        if upload_response.status_code == 200:
            upload_data = upload_response.json()
            file_uuid = upload_data["uuid"]
            print(f"✅ File uploaded successfully! UUID: {file_uuid}")
        else:
            print(f"❌ Upload failed: {upload_response.text}")
            return
    else:
        file_uuid = input("Enter UUID of already uploaded file: ").strip()
        if not file_uuid:
            print("❌ No file uploaded and no UUID provided")
            return

    # Step 1: Connect to WebSocket
    uri = "ws://localhost:8000/celonis/ws"
    print(f"Connecting to {uri}")

    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")

        # Receive connection confirmation and session ID
        connection_response = await websocket.recv()
        connection_data = json.loads(connection_response)
        print(f"Connection response: {connection_data}")

        if connection_data.get("type") != "connected":
            print("❌ Failed to establish connection")
            return

        session_id = connection_data.get("session_id")
        print(f"✅ Assigned session ID: {session_id}")

        # Step 2: Start login
        login_command = {
            "command": "start_login",
            "username": os.getenv("CELONIS_USERNAME"),
            "password": os.getenv("CELONIS_PASSWORD"),
        }

        print("Sending login command...")
        await websocket.send(json.dumps(login_command))

        response = await websocket.recv()
        response_data = json.loads(response)
        print(f"Login response: {response_data}")

        # Step 3: Handle MFA if required
        if response_data.get("type") == "mfa_required":
            mfa_code = input("Please enter your MFA code: ")

            mfa_command = {"command": "submit_mfa_code", "code": mfa_code}

            print("Sending MFA code...")
            await websocket.send(json.dumps(mfa_command))

            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"MFA response: {response_data}")

        # Step 4: Process data if login was successful
        if response_data.get("type") in ["login_success", "mfa_success"]:
            process_command = {
                "command": "download_and_create_types",
                "uuid": file_uuid,
            }

            print(f"Sending data processing command with UUID: {file_uuid}")
            await websocket.send(json.dumps(process_command))

            # Listen for multiple responses during processing
            while True:
                response = await websocket.recv()
                response_data = json.loads(response)
                print(f"Processing response: {response_data}")

                if response_data.get("type") == "types_creation_complete":
                    print("✓ Processing completed successfully!")
                    break
                elif response_data.get("type") == "error":
                    print(f"✗ Error during processing: {response_data.get('message')}")
                    break

        # Step 5: Close the session
        close_command = {"command": "close"}
        await websocket.send(json.dumps(close_command))

        response = await websocket.recv()
        response_data = json.loads(response)
        print(f"Close response: {response_data}")


if __name__ == "__main__":
    print("Celonis WebSocket API Test Client with R2 Upload")
    print("Make sure the FastAPI server is running on localhost:8000")
    print()

    try:
        asyncio.run(test_websocket_client())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
