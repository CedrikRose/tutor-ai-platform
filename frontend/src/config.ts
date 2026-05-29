// API Configuration for Production
// Uses relative URLs that work with Nginx proxy
const API_URL = '';
const WS_URL = window.location.protocol === 'https:'
  ? `wss://${window.location.host}`
  : `ws://${window.location.host}`;

export { API_URL, WS_URL };
