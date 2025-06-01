// Backend WebSocket message types
export interface ServerResponse {
  type:
    | "connected"
    | "login_success"
    | "login_failed"
    | "mfa_required"
    | "mfa_success"
    | "mfa_failed"
    | "download_started"
    | "download_complete"
    | "types_creation_started"
    | "types_creation_complete"
    | "error"
    | "closed"
    | "log_message";
  session_id?: string;
  message?: string;
  level?: "info" | "warning";
  [key: string]: any;
}

export interface ClientCommand {
  command:
    | "start_login"
    | "submit_mfa_code"
    | "download_and_create_types"
    | "retry_login"
    | "retry_mfa"
    | "close";
  username?: string;
  password?: string;
  code?: string;
  uuid?: string;
}

// Application state types
export type AppState =
  | "idle" // Initial state - ready for file upload
  | "uploading" // Uploading file to R2
  | "file_ready" // File uploaded successfully, ready to connect
  | "connecting" // Connecting to WebSocket
  | "connected" // Connected to WebSocket
  | "login_required" // WebSocket connected, waiting for login
  | "mfa_required" // MFA code required
  | "authenticated" // Successfully authenticated
  | "downloading" // Downloading file from R2
  | "creating_types" // Creating types in Celonis
  | "completed" // Process completed successfully
  | "error"; // Error state

export interface LogEntry {
  timestamp: string;
  level: "info" | "warning" | "error" | "success" | "debug";
  message: string;
}

export interface ConnectionStatus {
  connected: boolean;
  sessionId?: string;
  error?: string;
}
