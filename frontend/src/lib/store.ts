import { create } from "zustand";
import type {
  AppState,
  LogEntry,
  ConnectionStatus,
  ServerResponse,
  ClientCommand,
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
    const { websocket, addLog } = get();

    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
      addLog({ level: "error", message: "Not connected to backend" });
      return;
    }

    try {
      websocket.send(JSON.stringify(command));
      addLog({ level: "debug", message: `Sent command: ${command.command}` });
    } catch (error) {
      addLog({ level: "error", message: "Failed to send command" });
    }
  },
}));

// Handle server responses
function handleServerResponse(response: ServerResponse) {
  const { addLog, setAppState, connectionStatus } = useAppStore.getState();

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
      addLog({ level: "success", message: "Login successful" });
      break;

    case "login_failed":
      setAppState("login_required");
      addLog({ level: "error", message: response.message || "Login failed" });
      break;

    case "mfa_required":
      setAppState("mfa_required");
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
