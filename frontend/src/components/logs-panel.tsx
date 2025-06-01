import { useEffect, useRef } from "react";
import { useAppStore } from "@/lib/store";

export default function LogsPanel() {
  const { logs, clearLogs } = useAppStore();
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when logs update
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const getLevelColor = (level: string) => {
    switch (level) {
      case "error":
        return "text-red-400";
      case "warning":
        return "text-yellow-400";
      case "success":
        return "text-green-400";
      case "debug":
        return "text-purple-400";
      case "info":
      default:
        return "text-blue-400";
    }
  };

  return (
    <section className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xl font-mono text-gray-300">System Logs</h2>
        <div className="flex items-center space-x-2">
          <button
            onClick={clearLogs}
            className="text-xs font-mono text-gray-500 hover:text-gray-300 transition-colors"
            title="Clear logs"
          >
            CLEAR
          </button>
          <div className="h-2 w-2 rounded-full bg-red-500"></div>
          <div className="h-2 w-2 rounded-full bg-yellow-500"></div>
          <div className="h-2 w-2 rounded-full bg-green-500"></div>
        </div>
      </div>

      <div className="bg-black border border-gray-800 rounded-md h-80 overflow-y-auto font-mono text-sm p-4">
        {logs.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            No logs yet. Connect to backend to start seeing activity.
          </div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="mb-1 leading-relaxed">
              <span className="text-gray-500">[{log.timestamp}]</span>{" "}
              <span className={getLevelColor(log.level)}>[{log.level.toUpperCase()}]</span>{" "}
              <span className="text-gray-300">{log.message}</span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </section>
  );
}
