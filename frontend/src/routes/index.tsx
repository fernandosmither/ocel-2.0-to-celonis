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
      <main className="min-h-screen bg-black text-gray-100 pt-4 px-4 md:px-8 md:pt-8">
        <div className="max-w-6xl mx-auto space-y-8 mb-16">
          <Header title="Ocelonis" subtitle="Ocel 2.0 to Celonis Uploader" />

          <ControlPanel />

          <LogsPanel />
        </div>
        <footer className="bg-black border-t border-gray-800 pt-6">
          <div className="max-w-6xl mx-auto text-center">
            <a
              href="https://github.com/fernandosmither/ocel-2.0-to-celonis"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-300 transition-colors duration-300 hover:underline"
            >
              <img
                src="/github-mark-white.svg"
                alt="GitHub"
                className="w-4 h-4"
              />
              View Source Code
            </a>
          </div>
        </footer>
      </main>

      <a href="https://www.haplab.org/" target="_blank" rel="noopener">
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
