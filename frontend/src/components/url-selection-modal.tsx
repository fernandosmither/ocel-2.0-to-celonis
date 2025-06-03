import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Plus, ExternalLink } from "lucide-react";

interface UrlSelectionModalProps {
  isOpen: boolean;
  onUrlSelected: (url: string) => void;
}

const STORAGE_KEY = "celonis-alliance-urls";

interface SavedUrl {
  url: string;
  label: string;
  lastUsed: number;
}

export default function UrlSelectionModal({
  isOpen,
  onUrlSelected,
}: UrlSelectionModalProps) {
  const [savedUrls, setSavedUrls] = useState<SavedUrl[]>([]);
  const [selectedUrl, setSelectedUrl] = useState<string>("");
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [newLabel, setNewLabel] = useState("");

  // Load saved URLs from localStorage on component mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as SavedUrl[];
        // Sort by most recently used
        const sorted = parsed.sort((a, b) => b.lastUsed - a.lastUsed);
        setSavedUrls(sorted);
        if (sorted.length > 0) {
          setSelectedUrl(sorted[0].url);
        }
      }
    } catch (error) {
      console.error("Failed to load saved URLs:", error);
    }
  }, [isOpen]);

  const saveUrlToStorage = (url: string, label: string) => {
    try {
      const existing = savedUrls.filter((item) => item.url !== url);
      const newEntry: SavedUrl = {
        url,
        label: label || extractDomainFromUrl(url),
        lastUsed: Date.now(),
      };

      const updated = [newEntry, ...existing].slice(0, 5); // Keep only last 5
      setSavedUrls(updated);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    } catch (error) {
      console.error("Failed to save URL:", error);
    }
  };

  const extractDomainFromUrl = (url: string): string => {
    try {
      const domain = new URL(url).hostname;
      // Extract the academic alliance name from subdomain
      const match = domain.match(/^academic-([^.]+)/);
      return match ? match[1] : domain;
    } catch {
      return url;
    }
  };

  const handleSubmit = () => {
    let urlToUse = selectedUrl;

    if (isAddingNew) {
      if (!newUrl.trim()) return;

      // Validate URL format
      try {
        const url = new URL(newUrl.trim());
        if (!url.hostname.includes("celonis.cloud")) {
          alert("Please enter a valid Celonis Cloud URL");
          return;
        }
        urlToUse = url.toString().replace(/\/$/, ""); // Remove trailing slash
      } catch {
        alert("Please enter a valid URL");
        return;
      }

      saveUrlToStorage(urlToUse, newLabel.trim());
    } else {
      if (!urlToUse) return;

      // Update last used timestamp
      const existing = savedUrls.find((item) => item.url === urlToUse);
      if (existing) {
        saveUrlToStorage(existing.url, existing.label);
      }
    }

    onUrlSelected(urlToUse);
  };

  const handleAddNew = () => {
    setIsAddingNew(true);
    setSelectedUrl("");
    setNewUrl("");
    setNewLabel("");
  };

  const handleCancelAdd = () => {
    setIsAddingNew(false);
    if (savedUrls.length > 0) {
      setSelectedUrl(savedUrls[0].url);
    }
  };

  return (
    <Dialog open={isOpen}>
      <DialogContent className="bg-gray-900 border-gray-700 text-gray-100 sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl font-mono text-gray-200">
            <ExternalLink className="w-5 h-5" />
            Select Celonis Academic Alliance
          </DialogTitle>
          <DialogDescription className="text-gray-400 font-mono text-sm">
            Choose your Celonis academic alliance URL or add a new one.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {savedUrls.length > 0 && !isAddingNew && (
            <div className="space-y-3">
              <label className="block text-sm font-mono text-gray-300">
                Previously used alliances:
              </label>
              <div className="space-y-2">
                {savedUrls.map((item) => (
                  <label
                    key={item.url}
                    className="flex items-center space-x-3 cursor-pointer p-2 rounded-md hover:bg-gray-800"
                  >
                    <input
                      type="radio"
                      name="alliance-url"
                      value={item.url}
                      checked={selectedUrl === item.url}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                        setSelectedUrl(e.target.value)
                      }
                      className="text-cyan-500 focus:ring-cyan-500"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-gray-200">
                        {item.label}
                      </div>
                      <div className="text-xs text-gray-400 font-mono truncate">
                        {item.url}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}

          {isAddingNew && (
            <div className="space-y-3">
              <div>
                <label
                  htmlFor="newUrl"
                  className="block text-sm font-mono text-gray-300 mb-2"
                >
                  Alliance URL *
                </label>
                <input
                  id="newUrl"
                  type="url"
                  value={newUrl}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setNewUrl(e.target.value)
                  }
                  placeholder="https://academic-example.eu-2.celonis.cloud"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-md text-gray-100 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                />
              </div>
              <div>
                <label
                  htmlFor="newLabel"
                  className="block text-sm font-mono text-gray-300 mb-2"
                >
                  Label (optional)
                </label>
                <input
                  id="newLabel"
                  type="text"
                  value={newLabel}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setNewLabel(e.target.value)
                  }
                  placeholder="My University"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-md text-gray-100 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                />
              </div>
            </div>
          )}

          <div className="flex gap-2 pt-4">
            {!isAddingNew ? (
              <>
                <Button
                  variant="outline"
                  onClick={handleAddNew}
                  className="flex items-center gap-2 border-gray-600 bg-gray-800 hover:bg-gray-700 text-gray-300 font-mono"
                >
                  <Plus className="w-4 h-4" />
                  Add New Alliance
                </Button>
                <Button
                  onClick={handleSubmit}
                  disabled={!selectedUrl}
                  className="flex-1 bg-cyan-600 hover:bg-cyan-700 text-white font-mono"
                >
                  Continue
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="outline"
                  onClick={handleCancelAdd}
                  className="border-gray-600 bg-gray-800 hover:bg-gray-700 text-gray-300 font-mono"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSubmit}
                  disabled={!newUrl.trim()}
                  className="flex-1 bg-cyan-600 hover:bg-cyan-700 text-white font-mono"
                >
                  Add & Continue
                </Button>
              </>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
