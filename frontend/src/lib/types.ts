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
    | "failed_requests_snapshot"
    | "recovery_started"
    | "recovery_complete"
    | "error"
    | "closed"
    | "log_message";
  session_id?: string;
  message?: string;
  level?: "info" | "warning";
  summary?: FailedRequestsSummary;
  result?: RecoveryResult;
  pending?: number;
  delay_seconds?: number;
  limit?: number | null;
  [key: string]: any;
}

export interface ClientCommand {
  command:
    | "start_login"
    | "submit_mfa_code"
    | "download_and_create_types"
    | "retry_login"
    | "retry_mfa"
    | "list_failed_requests"
    | "retry_failed_requests"
    | "clear_failed_requests"
    | "close";
  base_url?: string;
  username?: string;
  password?: string;
  code?: string;
  uuid?: string;
  delay_ms?: number;
  limit?: number;
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

export type RecoveryStatus = "idle" | "ready" | "running";

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

export interface FailedRequestSummaryEntry {
  id: string;
  operation: string;
  created_at: string;
  metadata: Record<string, unknown>;
  attempt_count: number;
  last_status_code?: number | null;
  last_message?: string | null;
}

export interface FailedRequestsSummary {
  total: number;
  records: FailedRequestSummaryEntry[];
}

export interface RecoveryResultDetail {
  id: string;
  operation: string;
  status: "success" | "failed";
  status_code: number;
}

export interface RecoveryResult {
  total_available: number;
  selected: number;
  succeeded: number;
  failed: number;
  details: RecoveryResultDetail[];
}
