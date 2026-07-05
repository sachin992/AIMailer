import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

let isRefreshing = false;
let refreshSubscribers = [];

const getAccessToken = () => localStorage.getItem('accessToken');
const getRefreshToken = () => localStorage.getItem('refreshToken');

const setTokens = (accessToken, refreshToken) => {
  if (accessToken) {
    localStorage.setItem('accessToken', accessToken);
  }
  if (refreshToken) {
    localStorage.setItem('refreshToken', refreshToken);
  }
};

const clearTokens = () => {
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('adminUser');
};

const subscribeTokenRefresh = (callback) => {
  refreshSubscribers.push(callback);
};

const onRefreshed = (newToken) => {
  refreshSubscribers.forEach((callback) => callback(newToken));
  refreshSubscribers = [];
};

api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (!error.response) {
      return Promise.reject(error);
    }

    if (
      error.response.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url.includes('/auth/login') &&
      !originalRequest.url.includes('/auth/refresh')
    ) {
      originalRequest._retry = true;

      if (isRefreshing) {
        return new Promise((resolve) => {
          subscribeTokenRefresh((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api(originalRequest));
          });
        });
      }

      isRefreshing = true;

      try {
        const refreshToken = getRefreshToken();
        if (!refreshToken) {
          clearTokens();
          window.location.href = '/login';
          return Promise.reject(error);
        }

        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const newAccessToken = response.data.access_token;
        setTokens(newAccessToken, null);
        onRefreshed(newAccessToken);

        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        clearTokens();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// API Service
const apiService = {
  // Authentication
  login: (email, password) => api.post('/auth/login', { email, password }),

  register: (data) => api.post('/auth/register', data),

  refreshToken: (refreshToken) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }),

  getCurrentUser: () => api.get('/auth/me'),

  setTokens,
  clearTokens,

  // Health check
  healthCheck: () => api.get('/health'),

  // Configuration
  getConfig: () => api.get('/config'),

  // Emails
  getPendingReviewEmails: (limit = 50) =>
    api.get('/emails/pending-review', { params: { limit } }),

  getRecentEmails: (limit = 20) =>
    api.get('/emails/recent', { params: { limit } }),

  getEmailDetails: (emailId) =>
    api.get(`/emails/${emailId}`),

  approveAndSendResponse: (emailId, data) =>
    api.post(`/emails/${emailId}/approve-and-send`, data),

  generateCustomResponse: (emailId, instructions) =>
    api.post(`/emails/${emailId}/generate-response`, { instructions }),

  // Analytics
  getAnalyticsSummary: (period = 'weekly') =>
    api.get('/analytics/summary', { params: { period } }),

  getPerformanceInsights: () =>
    api.get('/analytics/insights'),

  exportAnalyticsReport: () =>
    api.post('/analytics/export'),
};

export default apiService;
