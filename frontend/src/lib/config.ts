// Configuration constants
export const CONFIG = {
  BACKEND_URL: import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000',
  WS_URL: (import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000').replace('http', 'ws') + '/celonis/ws',
  UPLOAD_URL: (import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000') + '/cloudflare/upload',
} as const;
