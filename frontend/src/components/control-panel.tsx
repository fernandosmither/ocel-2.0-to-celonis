import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { uploadFile, UploadError } from "@/lib/upload";
import LoginModal from "./login-modal";
import MfaModal from "./mfa-modal";
import UrlSelectionModal from "./url-selection-modal";
import RecoveryModal from "./recovery-modal";
import { Upload, Loader2 } from "lucide-react";

export default function ControlPanel() {
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showMfaModal, setShowMfaModal] = useState(false);
  const [showUrlModal, setShowUrlModal] = useState(false);
  const [showRecoveryModal, setShowRecoveryModal] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    appState,
    connectionStatus,
    uploadedFileUuid,
    uploadProgress,
    selectedBaseUrl,
    connect,
    disconnect,
    sendCommand,
    setUploadProgress,
    setUploading,
    setFileReady,
    setSelectedBaseUrl,
    addLog,
    recoverySummary,
    recoveryStatus,
    recoveryResult,
    requestRecoverySummary,
  } = useAppStore();

  // No automatic connection on mount - only connect after file upload
  useEffect(() => {
    // Only connect after successful file upload
    if (appState === "file_ready" && !connectionStatus.connected) {
      connect();
    }
  }, [appState, connectionStatus.connected, connect]);

  useEffect(() => {
    if (connectionStatus.connected) {
      requestRecoverySummary();
    }
  }, [connectionStatus.connected, requestRecoverySummary]);

  const pendingRecovery = recoverySummary?.total ?? 0;
  const hasRecoveryQueue = pendingRecovery > 0;

  // Only auto-open MFA modal when MFA is required
  useEffect(() => {
    if (appState === "mfa_required" && !showMfaModal) {
      setShowMfaModal(true);
    }
  }, [appState, showMfaModal]);

  // Close MFA modal when authentication is successful
  useEffect(() => {
    if (appState === "authenticated" && showMfaModal) {
      setShowMfaModal(false);
    }
  }, [appState, showMfaModal]);

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setUploading();
      addLog({ level: "info", message: `Starting upload of ${file.name}` });

      const result = await uploadFile(file, (progress) => {
        setUploadProgress(progress.percentage);
        addLog({
          level: "info",
          message: `Upload progress: ${progress.percentage}%`,
        });
      });

      setFileReady(result.uuid);
      addLog({
        level: "success",
        message: `File uploaded successfully. UUID: ${result.uuid}`,
      });
    } catch (error) {
      if (error instanceof UploadError) {
        addLog({ level: "error", message: `Upload failed: ${error.message}` });
      } else {
        addLog({ level: "error", message: "Upload failed: Unknown error" });
      }
      // Reset to idle state on error
      useAppStore.setState({ appState: "idle", uploadProgress: 0 });
    }

    // Clear file input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleStartLogin = () => {
    if (appState === "idle") {
      // If no file uploaded yet, prompt user to upload first
      addLog({
        level: "warning",
        message: "Please upload a .jsonocel file first",
      });
      return;
    } else if (!selectedBaseUrl) {
      // If no URL selected, show URL selection modal
      setShowUrlModal(true);
      return;
    } else {
      setShowLoginModal(true);
    }
  };

  const handleUrlSelected = (url: string) => {
    setSelectedBaseUrl(url);
    setShowUrlModal(false);
    addLog({
      level: "success",
      message: `Selected Celonis alliance: ${url}`,
    });
    // Automatically open login modal after URL selection
    setShowLoginModal(true);
  };

  const handleDownloadAndCreateTypes = () => {
    if (!uploadedFileUuid) {
      addLog({
        level: "error",
        message: "No file uploaded. Please upload a .jsonocel file first.",
      });
      return;
    }

    sendCommand({
      command: "download_and_create_types",
      uuid: uploadedFileUuid,
    });
  };

  const getAvailableActions = () => {
    const actions = [];

    // Always show close button if connected
    if (connectionStatus.connected) {
      actions.push({
        id: "close",
        label: "CLOSE CONNECTION",
        onClick: disconnect,
        variant: "destructive" as const,
      });
    }

    switch (appState) {
      case "idle":
        actions.unshift({
          id: "upload_file",
          label: "UPLOAD .JSONOCEL FILE",
          onClick: () => fileInputRef.current?.click(),
          variant: "default" as const,
          icon: <Upload className="w-4 h-4 mr-2" />,
        });
        break;

      case "connecting":
        actions.unshift({
          id: "connecting",
          label: "CONNECTING...",
          onClick: () => {},
          disabled: true,
          variant: "default" as const,
        });
        break;

      case "connected":
      case "login_required":
        actions.unshift({
          id: "start_login",
          label: selectedBaseUrl ? "START LOGIN" : "SELECT ALLIANCE & LOGIN",
          onClick: handleStartLogin,
          variant: "default" as const,
        });
        break;

      case "mfa_required":
        actions.unshift({
          id: "submit_mfa",
          label: "SUBMIT MFA CODE",
          onClick: () => setShowMfaModal(true),
          variant: "default" as const,
        });
        break;

      case "authenticated":
        actions.unshift({
          id: "download_and_create",
          label: "DOWNLOAD & CREATE TYPES",
          onClick: handleDownloadAndCreateTypes,
          variant: "default" as const,
        });
        break;

      case "uploading":
        actions.unshift({
          id: "uploading",
          label: `UPLOADING... ${uploadProgress}%`,
          onClick: () => {},
          disabled: true,
          variant: "default" as const,
          icon: <Loader2 className="w-4 h-4 mr-2 animate-spin" />,
        });
        break;

      case "downloading":
        actions.unshift({
          id: "downloading",
          label: "DOWNLOADING...",
          onClick: () => {},
          disabled: true,
          variant: "default" as const,
          icon: <Loader2 className="w-4 h-4 mr-2 animate-spin" />,
        });
        break;

      case "creating_types":
        actions.unshift({
          id: "creating_types",
          label: "CREATING TYPES...",
          onClick: () => {},
          disabled: true,
          variant: "default" as const,
          icon: <Loader2 className="w-4 h-4 mr-2 animate-spin" />,
        });
        break;

      case "completed":
        actions.unshift({
          id: "completed",
          label: "PROCESS COMPLETED ✓",
          onClick: () => {},
          disabled: true,
          variant: "default" as const,
        });
        break;

      case "error":
        actions.unshift({
          id: "retry",
          label: "RETRY CONNECTION",
          onClick: connect,
          variant: "default" as const,
        });
        break;
    }

    if (connectionStatus.connected) {
      actions.push({
        id: "refresh_recovery",
        label: "CHECK RECOVERY QUEUE",
        onClick: requestRecoverySummary,
        variant: "default" as const,
      });

      if (recoveryStatus === "running") {
        actions.unshift({
          id: "recovery_running",
          label: "RECOVERY IN PROGRESS...",
          onClick: () => setShowRecoveryModal(true),
          variant: "default" as const,
          disabled: true,
        });
      } else if (hasRecoveryQueue) {
        actions.unshift({
          id: "open_recovery",
          label: "OPEN RECOVERY MODE",
          onClick: () => setShowRecoveryModal(true),
          variant: "default" as const,
        });
      }
    }

    return actions;
  };

  const actions = getAvailableActions();

  return (
    <>
      <section className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-mono text-gray-300">Control Panel</h2>
          <div className="flex items-center space-x-2">
            <div
              className={`h-2 w-2 rounded-full ${
                connectionStatus.connected ? "bg-green-500" : "bg-red-500"
              }`}
            ></div>
            <span className="text-sm font-mono text-gray-400">
              {connectionStatus.connected ? "Connected" : "Disconnected"}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {actions.map((action) => (
            <Button
              key={action.id}
              variant={
                action.variant === "destructive" ? "destructive" : "outline"
              }
              className={`
                h-14 font-mono text-sm transition-all duration-200 relative overflow-hidden
                ${
                  action.variant === "destructive"
                    ? "border-red-700 bg-red-900 hover:bg-red-800 text-red-200"
                    : "border-gray-700 bg-gray-900 hover:bg-gray-800 text-gray-200"
                }
                ${action.disabled ? "opacity-50 cursor-not-allowed" : ""}
              `}
              onClick={action.onClick}
              disabled={action.disabled}
            >
              {action.icon}
              {action.label}
            </Button>
          ))}
        </div>

        {selectedBaseUrl && (
          <div className="mt-4 p-3 bg-gray-800 border border-gray-700 rounded-md">
            <p className="text-sm font-mono text-gray-300">
              Selected Alliance:{" "}
              <span className="text-cyan-400">{selectedBaseUrl}</span>
            </p>
          </div>
        )}

        {uploadedFileUuid && (
          <div className="mt-4 p-3 bg-gray-800 border border-gray-700 rounded-md">
            <p className="text-sm font-mono text-gray-300">
              File UUID:{" "}
              <span className="text-cyan-400">{uploadedFileUuid}</span>
            </p>
          </div>
        )}

        {recoverySummary && (
          <div className="mt-4 p-3 bg-gray-800 border border-gray-700 rounded-md space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-mono text-gray-300">
                Recovery queue:{" "}
                <span
                  className={hasRecoveryQueue ? "text-amber-300" : "text-green-400"}
                >
                  {pendingRecovery} pending
                </span>
              </p>
              {hasRecoveryQueue && (
                <Button
                  variant="outline"
                  onClick={() => setShowRecoveryModal(true)}
                  className="border-gray-600 bg-gray-800 hover:bg-gray-700 text-gray-200 font-mono text-xs"
                >
                  Open Recovery
                </Button>
              )}
            </div>
            {recoverySummary.records.slice(0, 3).map((record) => (
              <div key={record.id} className="text-xs font-mono text-gray-400">
                <span className="text-cyan-400">{record.operation}</span>{" "}
                <span>
                  • attempts: {record.attempt_count} • status:{" "}
                  {record.last_status_code ?? "n/a"}
                </span>
              </div>
            ))}
            {recoverySummary.records.length > 3 && (
              <p className="text-xs font-mono text-gray-500">
                +{recoverySummary.records.length - 3} more operations in queue.
              </p>
            )}
          </div>
        )}

        {recoveryResult && (
          <div className="mt-4 p-3 bg-gray-800 border border-gray-700 rounded-md">
            <p className="text-sm font-mono text-gray-300">
              Last recovery run:{" "}
              <span className="text-green-400">{recoveryResult.succeeded}</span>{" "}
              succeeded,{" "}
              <span className="text-red-300">{recoveryResult.failed}</span> failed.
            </p>
          </div>
        )}
      </section>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".jsonocel"
        onChange={handleFileUpload}
        style={{ display: "none" }}
      />

      {/* Modals */}
      <UrlSelectionModal isOpen={showUrlModal} onUrlSelected={handleUrlSelected} />
      <LoginModal open={showLoginModal} onOpenChange={setShowLoginModal} />
      <MfaModal open={showMfaModal} onOpenChange={setShowMfaModal} />
      <RecoveryModal open={showRecoveryModal} onOpenChange={setShowRecoveryModal} />
    </>
  );
}
