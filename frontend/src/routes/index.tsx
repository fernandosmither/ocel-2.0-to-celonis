import { createFileRoute } from "@tanstack/react-router";
import Header from "@/components/header";
import ControlPanel from "@/components/control-panel";
import LogsPanel from "@/components/logs-panel";

export const Route = createFileRoute("/")({
  component: App,
});

function App() {
  return (
    <div className="App">
      <main className="min-h-screen bg-black text-gray-100 p-4 md:p-8">
        <div className="max-w-6xl mx-auto space-y-8">
          <Header title="Ocelonis" subtitle="Ocel 2.0 to Celonis Uploader" />

          <ControlPanel />

          <LogsPanel />
        </div>
      </main>

      <a href="https://www.haplab.org/"
      target="_blank"
      rel="noopener"
      >
      <div className="fixed bottom-4 right-4 z-10 group">
        <img
          src="/haplab-logo-upscaled.png"
          alt="HapLab - Created by"
          className="w-12 h-12 md:w-16 md:h-16 opacity-60 hover:opacity-90 transition-opacity duration-300 cursor-pointer filter grayscale hover:grayscale-0"
            title="Created by HapLab"
          />
        </div>
      </a>
    </div>
  );
}
