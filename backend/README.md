# Celonis WebSocket API with Cloudflare R2 Storage

A FastAPI-based WebSocket service for interacting with Celonis APIs. This service provides a command-based interface for uploading files to Cloudflare R2, logging into Celonis, handling MFA authentication, and creating object/event types from JSONOCEL files.

## Features

- **File Upload**: Upload .jsonocel files to Cloudflare R2 storage
- **Session Management**: Each WebSocket connection maintains its own isolated session
- **Automatic Cleanup**: Sessions automatically expire after 5 minutes of inactivity
- **MFA Support**: Handles multi-factor authentication workflows
- **Async Operations**: All operations are asynchronous for better performance
- **Error Handling**: Comprehensive error handling with retry capabilities

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for package management.

1. Install dependencies:
```bash
uv sync
```

2. Activate the virtual environment:
```bash
source .venv/bin/activate
```

3. Configure environment variables:
```bash
# Add these to your .env file
CELONIS_USERNAME=your_username
CELONIS_PASSWORD=your_password
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_key
```

## Running the Server

```bash
fastapi dev
```

The server will start on `http://localhost:8000` with:
- WebSocket endpoint: `ws://localhost:8000/celonis/ws`
- File upload endpoint: `POST /cloudflare/upload`

## API Endpoints

### File Upload

**POST** `/cloudflare/upload`

Upload a .jsonocel file to Cloudflare R2 storage.

**Request**: `multipart/form-data` with file
**Response**: 
```json
{
  "uuid": "123e4567-e89b-12d3-a456-426614174000"
}
```

### Example Usage:
```bash
curl -X POST "http://localhost:8000/cloudflare/upload" \
  -F "file=@your-file.jsonocel"
```

## WebSocket API

### Connection

Connect to: `ws://localhost:8000/celonis/ws`

Upon connection, the server will automatically assign a unique session ID and send it to the client:

```json
{
  "type": "connected",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Connected with session ID: 123e4567-e89b-12d3-a456-426614174000"
}
```

### Command Format

All commands are sent as JSON with the following structure:

```json
{
  "command": "command_name",
  "param1": "value1",
  "param2": "value2"
}
```

### Available Commands

#### 1. Start Login
```json
{
  "command": "start_login",
  "username": "your_username",
  "password": "your_password"
}
```

**Responses:**
- `login_success`: Login completed successfully
- `mfa_required`: MFA authentication needed
- `login_failed`: Login failed
- `error`: Error occurred

#### 2. Submit MFA Code
```json
{
  "command": "submit_mfa_code",
  "code": "123456"
}
```

**Responses:**
- `mfa_success`: MFA completed successfully
- `mfa_failed`: Invalid MFA code
- `error`: Error occurred

#### 3. Download and Create Types
```json
{
  "command": "download_and_create_types",
  "uuid": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Responses:**
- `download_started`: Download began
- `download_complete`: Download finished
- `types_creation_started`: Type creation began
- `types_creation_complete`: All types created successfully
- `error`: Error occurred

#### 4. Retry Commands
```json
{
  "command": "retry_login",
  "username": "your_username",
  "password": "your_password"
}
```

```json
{
  "command": "retry_mfa",
  "code": "123456"
}
```

#### 5. Close Session
```json
{
  "command": "close"
}
```

**Response:**
- `closed`: Session closed successfully

### Response Format

All responses follow this format:

```json
{
  "type": "response_type",
  "message": "optional error message",
  "additional": "optional data"
}
```

### Complete Workflow

1. **Upload File**: POST file to `/cloudflare/upload` → receive UUID
2. **Connect**: Connect to WebSocket at `ws://localhost:8000/celonis/ws`
3. **Session**: Receive `connected` response with your assigned session ID
4. **Login**: Send `start_login` command
5. **MFA**: If `mfa_required` received, send `submit_mfa_code`
6. **Process**: Once authenticated, send `download_and_create_types` with UUID
7. **Monitor**: Watch responses until `types_creation_complete`
8. **Close**: Send `close` to end session

## Testing

Run the test client:

```bash
python test_client.py
```

The test client demonstrates the complete workflow including file upload and can be used as a reference implementation.

## Architecture

The codebase is structured as follows:

- `main.py`: FastAPI application and router registration
- `enums.py`: Command and response type definitions
- `test_client.py`: Example client implementation
- `celonis/`: Celonis integration module
  - `router.py`: WebSocket endpoint and handlers
  - `client.py`: Celonis API client
- `cloudflare/`: Cloudflare R2 integration module
  - `router.py`: File upload endpoint
  - `client.py`: R2 storage operations
  - `config.py`: R2 configuration settings

## Session Management

- Sessions automatically expire after 5 minutes of inactivity
- Each session maintains its own CelonisClient instance
- Sessions are automatically cleaned up on disconnect
- Multiple concurrent sessions are supported

## Error Handling

The API provides detailed error messages for:
- Authentication failures
- Network errors
- Invalid JSON format
- Missing required parameters
- File upload/download errors
- Celonis API errors

All errors include descriptive messages to help with debugging.
