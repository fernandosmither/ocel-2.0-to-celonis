import { create } from "zustand";
import type {
  AppState,
  LogEntry,
  ConnectionStatus,
  ServerResponse,
  ClientCommand,
  FailedRequestsSummary,
  RecoveryStatus,
  RecoveryResult,
} from "./types";
import { CONFIG } from "./config";

interface AppStore {
  // Connection state
  appState: AppState;
  connectionStatus: ConnectionStatus;
  websocket: WebSocket | null;

  // Logs
  logs: LogEntry[];

  // File upload
  uploadedFileUuid: string | null;
  uploadProgress: number;

  // Selected Celonis base URL
  selectedBaseUrl: string | null;

  // Login error state
  loginError: string | null;

  // Recovery queue state
  recoverySummary: FailedRequestsSummary | null;
  recoveryStatus: RecoveryStatus;
  recoveryResult: RecoveryResult | null;

  // Actions
  setAppState: (state: AppState) => void;
  addLog: (log: Omit<LogEntry, "timestamp">) => void;
  clearLogs: () => void;

  // WebSocket actions
  connect: () => void;
  disconnect: () => void;
  sendCommand: (command: ClientCommand) => void;

  // File upload actions
  setUploadedFileUuid: (uuid: string | null) => void;
  setUploadProgress: (progress: number) => void;

  // URL selection actions
  setSelectedBaseUrl: (url: string | null) => void;

  // Upload state management
  setUploading: () => void;
  setFileReady: (uuid: string) => void;

  // Login error management
  setLoginError: (error: string | null) => void;

  // Recovery management
  setRecoverySummary: (summary: FailedRequestsSummary | null) => void;
  setRecoveryStatus: (status: RecoveryStatus) => void;
  setRecoveryResult: (result: RecoveryResult | null) => void;
  requestRecoverySummary: () => void;
  startRecovery: (options?: { delayMs?: number; limit?: number }) => void;
  clearRecoveryQueue: () => void;
}

export const useAppStore = create<AppStore>((set, get) => ({
  // Initial state
  appState: "idle",
  connectionStatus: { connected: false },
  websocket: null,
  logs: [],
  uploadedFileUuid: null,
  uploadProgress: 0,
  selectedBaseUrl: null,
  loginError: null,
  recoverySummary: null,
  recoveryStatus: "idle",
  recoveryResult: null,

  // Basic actions
  setAppState: (state) => set({ appState: state }),

  addLog: (log) =>
    set((state) => ({
      logs: [
        ...state.logs,
        {
          ...log,
          timestamp: new Date()
            .toISOString()
            .replace("T", " ")
            .substring(0, 19),
        },
      ],
    })),

  clearLogs: () => set({ logs: [] }),

  setUploadedFileUuid: (uuid) => set({ uploadedFileUuid: uuid }),
  setUploadProgress: (progress) => set({ uploadProgress: progress }),
  setSelectedBaseUrl: (url) => set({ selectedBaseUrl: url }),

  // Upload state management
  setUploading: () => set({ appState: "uploading", uploadProgress: 0 }),
  setFileReady: (uuid: string) =>
    set({
      appState: "file_ready",
      uploadedFileUuid: uuid,
      uploadProgress: 100,
    }),

  // WebSocket actions
  connect: () => {
    const { websocket, appState, addLog } = get();

    // Don't connect if already connected or connecting
    if (websocket?.readyState === WebSocket.OPEN || appState === "connecting") {
      addLog({
        level: "debug",
        message: `Connection attempt skipped - current state: ${appState}, websocket readyState: ${websocket?.readyState}`,
      });
      return;
    }

    // Close existing websocket if it exists but not open
    if (websocket && websocket.readyState !== WebSocket.OPEN) {
      addLog({
        level: "debug",
        message: `Closing stale websocket (readyState: ${websocket.readyState})`,
      });
      websocket.close();
    }

    set({ appState: "connecting" });
    addLog({ level: "info", message: "Connecting to backend..." });

    try {
      const ws = new WebSocket(CONFIG.WS_URL);

      // Set websocket immediately to prevent duplicate connections
      set({ websocket: ws });
      addLog({
        level: "debug",
        message: `Created new websocket, readyState: ${ws.readyState}`,
      });

      ws.onopen = () => {
        const currentState = get();
        // Only update if this is still the current websocket
        if (currentState.websocket === ws) {
          set({
            connectionStatus: { connected: true },
            appState: "connected",
          });
          addLog({ level: "success", message: "Connected to backend" });
        } else {
          addLog({
            level: "debug",
            message: "Ignoring onopen for stale websocket",
          });
        }
      };

      ws.onmessage = (event) => {
        const currentState = get();
        // Only handle if this is still the current websocket
        if (currentState.websocket === ws) {
          try {
            const response: ServerResponse = JSON.parse(event.data);
            handleServerResponse(response);
          } catch (error) {
            addLog({
              level: "error",
              message: "Failed to parse server message",
            });
          }
        }
      };

      ws.onclose = (event) => {
        const currentState = get();
        // Only handle if this is still the current websocket
        if (currentState.websocket === ws) {
          set({
            websocket: null,
            connectionStatus: { connected: false },
            appState: "idle",
          });
          // Only log if it wasn't a manual disconnect
          if (!event.wasClean) {
            addLog({ level: "warning", message: "Disconnected from backend" });
          }
        }
      };

      ws.onerror = () => {
        const currentState = get();
        // Only handle if this is still the current websocket
        if (currentState.websocket === ws) {
          set({
            connectionStatus: { connected: false, error: "Connection failed" },
            appState: "error",
          });
          addLog({ level: "error", message: "Connection error occurred" });
        }
      };
    } catch (error) {
      set({ appState: "error", websocket: null });
      addLog({
        level: "error",
        message: "Failed to create WebSocket connection",
      });
    }
  },

  disconnect: () => {
    const { websocket, addLog } = get();

    if (websocket) {
      // Close cleanly
      websocket.close(1000, "User disconnect");
      addLog({ level: "info", message: "Disconnecting from backend..." });
    }

    set({
      websocket: null,
      connectionStatus: { connected: false },
      appState: "idle",
    });
  },

  sendCommand: (command) => {
    const { websocket, addLog, setLoginError } = get();

    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
      addLog({ level: "error", message: "Not connected to backend" });
      return;
    }

    // Clear login error when starting a new login attempt
    if (command.command === "start_login") {
      setLoginError(null);
    }

    try {
      websocket.send(JSON.stringify(command));
      addLog({ level: "debug", message: `Sent command: ${command.command}` });
    } catch (error) {
      addLog({ level: "error", message: "Failed to send command" });
    }
  },

  // Login error management
  setLoginError: (error) => set({ loginError: error }),

  // Recovery management
  setRecoverySummary: (summary) =>
    set((state) => ({
      recoverySummary: summary,
      recoveryStatus: summary && summary.total > 0 ? "ready" : "idle",
      recoveryResult: summary && summary.total > 0 ? state.recoveryResult : null,
    })),

  setRecoveryStatus: (status) => set({ recoveryStatus: status }),

  setRecoveryResult: (result) => set({ recoveryResult: result }),

  requestRecoverySummary: () => {
    const { sendCommand, addLog } = get();
    addLog({
      level: "info",
      message: "Requesting recovery queue snapshot",
    });
    sendCommand({ command: "list_failed_requests" });
  },

  startRecovery: (options = {}) => {
    const { sendCommand, addLog } = get();
    const payload: ClientCommand = {
      command: "retry_failed_requests",
    };

    if (typeof options.delayMs === "number") {
      payload.delay_ms = options.delayMs;
    }
    if (typeof options.limit === "number" && options.limit > 0) {
      payload.limit = options.limit;
    }

    set({ recoveryStatus: "running", recoveryResult: null });

    const pieces = [];
    if (payload.delay_ms !== undefined) {
      pieces.push(`delay ${payload.delay_ms}ms`);
    }
    if (payload.limit !== undefined) {
      pieces.push(`limit ${payload.limit}`);
    }

    addLog({
      level: "info",
      message:
        "Starting recovery run" +
        (pieces.length ? ` (${pieces.join(", ")})` : ""),
    });

    sendCommand(payload);
  },

  clearRecoveryQueue: () => {
    const { sendCommand, addLog } = get();
    addLog({
      level: "info",
      message: "Clearing recovery queue",
    });
    sendCommand({ command: "clear_failed_requests" });
  },
}));

// Handle server responses
function handleServerResponse(response: ServerResponse) {
  const {
    addLog,
    setAppState,
    connectionStatus,
    setLoginError,
    setRecoverySummary,
    setRecoveryStatus,
    setRecoveryResult,
  } = useAppStore.getState();

  switch (response.type) {
    case "connected":
      if (response.session_id) {
        useAppStore.setState({
          connectionStatus: {
            ...connectionStatus,
            sessionId: response.session_id,
          },
          appState: "login_required",
        });
      }
      addLog({
        level: "success",
        message: response.message || "Connected to server",
      });
      break;

    case "login_success":
      setAppState("authenticated");
      setLoginError(null);
      addLog({ level: "success", message: "Login successful" });
      break;

    case "login_failed":
      setAppState("login_required");
      setLoginError(response.message || "Login failed. Please check your credentials and try again.");
      addLog({ level: "error", message: response.message || "Login failed" });
      break;

    case "mfa_required":
      setAppState("mfa_required");
      setLoginError(null);
      addLog({ level: "info", message: "MFA authentication required" });
      break;

    case "mfa_success":
      setAppState("authenticated");
      addLog({ level: "success", message: "MFA authentication successful" });
      break;

    case "mfa_failed":
      setAppState("mfa_required");
      addLog({
        level: "error",
        message: response.message || "MFA authentication failed",
      });
      break;

    case "download_started":
      setAppState("downloading");
      addLog({ level: "info", message: "Download started" });
      break;

    case "download_complete":
      addLog({ level: "success", message: "Download completed" });
      break;

    case "types_creation_started":
      setAppState("creating_types");
      addLog({ level: "info", message: "Creating types in Celonis" });
      break;

    case "types_creation_complete":
      setAppState("completed");
      addLog({
        level: "success",
        message: "Types creation completed successfully",
      });
      break;

    case "failed_requests_snapshot":
      if (response.summary) {
        setRecoverySummary(response.summary);
        if (response.summary.total > 0) {
          addLog({
            level: "warning",
            message: `${response.summary.total} requests pending recovery`,
          });
        } else {
          addLog({
            level: "info",
            message: "Recovery queue is empty",
          });
        }
      } else {
        setRecoverySummary(null);
      }
      break;

    case "recovery_started": {
      setRecoveryStatus("running");
      const parts = [];
      if (typeof response.pending === "number") {
        parts.push(`${response.pending} queued requests`);
      }
      if (typeof response.delay_seconds === "number") {
        parts.push(`delay ${response.delay_seconds}s`);
      }
      if (typeof response.limit === "number") {
        parts.push(`limit ${response.limit}`);
      }
      addLog({
        level: "info",
        message: `Recovery started${parts.length ? ` (${parts.join(", ")})` : ""}`,
      });
      break;
    }

    case "recovery_complete": {
      const result = response.result as RecoveryResult | undefined;
      if (result) {
        setRecoveryResult(result);
        const level = result.failed > 0 ? "warning" : "success";
        addLog({
          level,
          message: `Recovery completed: ${result.succeeded} succeeded, ${result.failed} failed`,
        });
        setRecoveryStatus(result.failed > 0 ? "ready" : "idle");
      } else {
        addLog({
          level: "info",
          message: "Recovery completed",
        });
        setRecoveryStatus("idle");
      }
      break;
    }

    case "error":
      setAppState("error");
      addLog({
        level: "error",
        message: response.message || "An error occurred",
      });
      break;

    case "closed":
      setAppState("idle");
      addLog({ level: "info", message: "Session closed" });
      break;

    case "log_message":
      if (response.level && response.message) {
        addLog({
          level: response.level === "warning" ? "warning" : "info",
          message: response.message,
        });
      }
      break;

    default:
      addLog({ level: "debug", message: `Unknown response: ${response.type}` });
  }
}
