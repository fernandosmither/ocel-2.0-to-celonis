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

interface MfaModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function MfaModal({ open, onOpenChange }: MfaModalProps) {
  const [mfaCode, setMfaCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const { sendCommand, appState } = useAppStore();

  // Close modal when MFA is successful
  useEffect(() => {
    if (open && appState === "authenticated") {
      setIsLoading(false);
      onOpenChange(false);
    }
  }, [appState, open, onOpenChange]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!mfaCode.trim()) {
      return;
    }

    setIsLoading(true);

    sendCommand({
      command: "submit_mfa_code",
      code: mfaCode.trim(),
    });

    // Don't clear form or close modal here - let the useEffect handle it based on response
  };

  const handleCancel = () => {
    setMfaCode("");
    setIsLoading(false);
    onOpenChange(false);
  };

  // Clear form when modal closes
  useEffect(() => {
    if (!open) {
      setMfaCode("");
      setIsLoading(false);
    }
  }, [open]);

  // Auto-format MFA code (typically 6 digits)
  const handleMfaCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, "").slice(0, 12);
    setMfaCode(value);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-gray-900 border-gray-700 text-gray-100 sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-xl font-mono text-gray-200">
            Multi-Factor Authentication
          </DialogTitle>
          <DialogDescription className="text-gray-400 font-mono text-sm">
            Enter the 2FA code from your email
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label
              htmlFor="mfaCode"
              className="block text-sm font-mono text-gray-300 mb-2"
            >
              Authentication Code
            </label>
            <input
              id="mfaCode"
              type="text"
              value={mfaCode}
              onChange={handleMfaCodeChange}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-md text-gray-100 font-mono text-lg text-center tracking-widest focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder="000000000000"
              disabled={isLoading}
              autoComplete="one-time-code"
            />
            <p className="text-xs text-gray-500 font-mono mt-2">
              Enter the 2FA code exactly as shown in your email
            </p>
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
              disabled={isLoading || mfaCode.length < 6}
              className="bg-cyan-600 hover:bg-cyan-700 text-white font-mono"
            >
              {isLoading ? "Verifying..." : "Verify"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
