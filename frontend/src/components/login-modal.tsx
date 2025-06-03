import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAppStore } from "@/lib/store";

interface LoginModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function LoginModal({ open, onOpenChange }: LoginModalProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const { sendCommand, appState, selectedBaseUrl } = useAppStore();

  // Close modal when login is successful or MFA is required
  useEffect(() => {
    if (open && (appState === "mfa_required" || appState === "authenticated")) {
      setIsLoading(false);
      onOpenChange(false);
    }
  }, [appState, open, onOpenChange]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!username.trim() || !password.trim() || !selectedBaseUrl) {
      return;
    }

    setIsLoading(true);

    sendCommand({
      command: "start_login",
      base_url: selectedBaseUrl,
      username: username.trim(),
      password: password.trim(),
    });

    // Don't clear form or close modal here - let the useEffect handle it based on response
  };

  const handleCancel = () => {
    setUsername("");
    setPassword("");
    setIsLoading(false);
    onOpenChange(false);
  };

  // Clear form when modal closes
  useEffect(() => {
    if (!open) {
      setUsername("");
      setPassword("");
      setIsLoading(false);
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-gray-900 border-gray-700 text-gray-100 sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-xl font-mono text-gray-200">
            Celonis Login
          </DialogTitle>
          <DialogDescription className="text-gray-400 font-mono text-sm">
            Enter your Celonis credentials to authenticate
            {selectedBaseUrl && (
              <div className="mt-2 text-xs text-cyan-400">
                Alliance: {selectedBaseUrl}
              </div>
            )}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            <div>
              <label
                htmlFor="username"
                className="block text-sm font-mono text-gray-300 mb-2"
              >
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-md text-gray-100 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                placeholder="your.username@domain.com"
                disabled={isLoading}
                autoComplete="username"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-mono text-gray-300 mb-2"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-md text-gray-100 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                placeholder="••••••••"
                disabled={isLoading}
                autoComplete="current-password"
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              disabled={isLoading}
              className="border-gray-600 bg-gray-800 hover:bg-gray-700 text-gray-300 font-mono"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={
                isLoading ||
                !username.trim() ||
                !password.trim() ||
                !selectedBaseUrl
              }
              className="bg-cyan-600 hover:bg-cyan-700 text-white font-mono"
            >
              {isLoading ? "Authenticating..." : "Login"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
