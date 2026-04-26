import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercept requests to add JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Intercept responses to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const res = await axios.post(`${API_URL}/api/v1/auth/token/refresh/`, {
            refresh: refreshToken,
          });
          const { access, refresh } = res.data;
          localStorage.setItem('access_token', access);
          if (refresh) localStorage.setItem('refresh_token', refresh);
          originalRequest.headers.Authorization = `Bearer ${access}`;
          return api(originalRequest);
        } catch (refreshError) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      } else {
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// --- Auth ---
export const login = async (username, password) => {
  const res = await axios.post(`${API_URL}/api/v1/auth/token/`, { username, password });
  const { access, refresh } = res.data;
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
  return res.data;
};

export const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
};

export const isAuthenticated = () => !!localStorage.getItem('access_token');

// --- Merchant ---
export const getMerchantProfile = () => api.get('/merchants/me/');
export const getMerchantBalance = () => api.get('/merchants/me/balance/');
export const getMerchantLedger = (page = 1) => api.get(`/merchants/me/ledger/?page=${page}`);
export const getMerchantPayouts = (page = 1) => api.get(`/merchants/me/payouts/?page=${page}`);

// --- Payouts ---
export const createPayout = (data, idempotencyKey) =>
  api.post('/payouts/', data, {
    headers: { 'Idempotency-Key': idempotencyKey },
  });

export const getPayoutDetail = (id) => api.get(`/payouts/${id}/`);

export default api;
