from enum import Enum


class ClientCommand(str, Enum):
    START_LOGIN = "start_login"
    SUBMIT_MFA_CODE = "submit_mfa_code"
    DOWNLOAD_AND_CREATE_TYPES = "download_and_create_types"
    RETRY_LOGIN = "retry_login"
    RETRY_MFA = "retry_mfa"
    CLOSE = "close"


class ServerResponse(str, Enum):
    CONNECTED = "connected"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    MFA_REQUIRED = "mfa_required"
    MFA_SUCCESS = "mfa_success"
    MFA_FAILED = "mfa_failed"
    DOWNLOAD_STARTED = "download_started"
    DOWNLOAD_COMPLETE = "download_complete"
    TYPES_CREATION_STARTED = "types_creation_started"
    TYPES_CREATION_COMPLETE = "types_creation_complete"
    ERROR = "error"
    CLOSED = "closed"
    LOG_MESSAGE = "log_message"
