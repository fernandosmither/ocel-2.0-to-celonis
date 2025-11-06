import { useEffect, useMemo, useState } from "react";
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

interface RecoveryModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function RecoveryModal({ open, onOpenChange }: RecoveryModalProps) {
  const {
    recoverySummary,
    recoveryStatus,
    recoveryResult,
    requestRecoverySummary,
    startRecovery,
    clearRecoveryQueue,
  } = useAppStore();

  const [delayMs, setDelayMs] = useState<number>(1000);
  const [limit, setLimit] = useState<number | undefined>(undefined);

  const isRunning = recoveryStatus === "running";
  const hasQueue = (recoverySummary?.total ?? 0) > 0;

  useEffect(() => {
    if (open) {
      requestRecoverySummary();
    }
  }, [open, requestRecoverySummary]);

  useEffect(() => {
    if (!open) {
      setDelayMs(1000);
      setLimit(undefined);
    }
  }, [open]);

  const sortedRecords = useMemo(
    () => recoverySummary?.records ?? [],
    [recoverySummary?.records],
  );

  const handleStart = (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasQueue || isRunning) return;
    startRecovery({
      delayMs,
      limit,
    });
  };

  const handleClear = () => {
    clearRecoveryQueue();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-gray-900 border-gray-700 text-gray-100 max-w-3xl">
        <DialogHeader>
          <DialogTitle className="text-xl font-mono text-gray-200">
            Recovery Mode
          </DialogTitle>
          <DialogDescription className="text-gray-400 font-mono text-sm">
            Retry previously failed Celonis requests with custom timing controls.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          <section className="bg-gray-800/60 border border-gray-700 rounded-md p-4">
            <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
              <div>
                <p className="text-sm font-mono text-gray-300">
                  Pending requests:{" "}
                  <span className="text-cyan-400">
                    {recoverySummary?.total ?? 0}
                  </span>
                </p>
                <p className="text-xs font-mono text-gray-400">
                  Configure delay and batch size before starting a recovery run.
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={requestRecoverySummary}
                  disabled={isRunning}
                  className="border-gray-600 bg-gray-800 hover:bg-gray-700 text-gray-100 font-mono text-xs px-3 py-2"
                >
                  Refresh Queue
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleClear}
                  disabled={!hasQueue || isRunning}
                  className="border-red-700 bg-red-900 hover:bg-red-800 text-red-100 font-mono text-xs px-3 py-2"
                >
                  Clear Queue
                </Button>
              </div>
            </div>

            <form onSubmit={handleStart} className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono text-gray-400 mb-2">
                  Delay between requests (ms)
                </label>
                <input
                  type="number"
                  min={0}
                  step={50}
                  value={delayMs}
                  disabled={isRunning}
                  onChange={(event) => setDelayMs(Number(event.target.value))}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-gray-100 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-gray-400 mb-2">
                  Max requests per run (optional)
                </label>
                <input
                  type="number"
                  min={1}
                  value={limit ?? ""}
                  disabled={isRunning}
                  placeholder="All pending"
                  onChange={(event) => {
                    const raw = event.target.value;
                    setLimit(raw ? Number(raw) : undefined);
                  }}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-gray-100 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                />
              </div>

              <DialogFooter className="md:col-span-2 flex flex-col gap-2">
                <Button
                  type="submit"
                  disabled={!hasQueue || isRunning}
                  className="bg-cyan-600 hover:bg-cyan-700 text-white font-mono"
                >
                  {isRunning ? "Running recovery..." : "Start Recovery"}
                </Button>
              </DialogFooter>
            </form>
          </section>

          <section className="space-y-3">
            <h3 className="text-sm font-mono text-gray-300">
              Pending requests
            </h3>
            <div className="max-h-56 overflow-y-auto border border-gray-800 rounded-md divide-y divide-gray-800">
              {sortedRecords.length === 0 && (
                <p className="text-xs font-mono text-gray-500 px-4 py-6 text-center">
                  No failed requests queued.
                </p>
              )}
              {sortedRecords.map((record) => (
                <div
                  key={record.id}
                  className="px-4 py-3 bg-gray-900 text-xs font-mono text-gray-200"
                >
                  <div className="flex justify-between gap-2">
                    <span className="text-cyan-400">{record.operation}</span>
                    <span className="text-gray-500">
                      Attempts: {record.attempt_count}
                    </span>
                  </div>
                  <div className="mt-1 text-gray-400">
                    <span>ID: {record.id}</span>
                  </div>
                  {record.last_status_code !== null &&
                    record.last_status_code !== undefined && (
                      <div className="mt-1 text-gray-400">
                        <span>
                          Last status: {record.last_status_code}{" "}
                          {record.last_message && (
                            <span className="text-gray-500">
                              – {record.last_message}
                            </span>
                          )}
                        </span>
                      </div>
                    )}
                  {Object.keys(record.metadata || {}).length > 0 && (
                    <div className="mt-1 text-gray-500">
                      <span>Metadata: </span>
                      <code className="break-words">
                        {JSON.stringify(record.metadata)}
                      </code>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>

          {recoveryResult && (
            <section className="bg-gray-800/60 border border-gray-700 rounded-md p-4 space-y-2">
              <h3 className="text-sm font-mono text-gray-300">Last run summary</h3>
              <p className="text-xs font-mono text-gray-400">
                Selected: {recoveryResult.selected} • Succeeded:{" "}
                <span className="text-green-400">{recoveryResult.succeeded}</span> •
                Failed:{" "}
                <span className="text-red-300">{recoveryResult.failed}</span>
              </p>
              {recoveryResult.details.length > 0 && (
                <div className="max-h-32 overflow-y-auto border border-gray-800 rounded-md">
                  {recoveryResult.details.map((detail) => (
                    <div
                      key={`${detail.id}-${detail.status}`}
                      className="px-3 py-2 text-xs font-mono text-gray-200 bg-gray-900 border-b border-gray-800 last:border-b-0"
                    >
                      <span className="text-cyan-400">{detail.operation}</span>{" "}
                      <span
                        className={
                          detail.status === "success"
                            ? "text-green-400"
                            : "text-red-300"
                        }
                      >
                        {detail.status} ({detail.status_code})
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

