// API Configuration
// Uses environment variable from .env file (set by Vite)
const API_URL = import.meta.env.VITE_API_URL || '';
const WS_URL = import.meta.env.VITE_WS_URL || (
  window.location.protocol === 'https:'
    ? `wss://${window.location.host}`
    : `ws://${window.location.host}`
);

export { API_URL, WS_URL };
