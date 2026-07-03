import axios from 'axios';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 120000
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      error.message = detail;
    }

    if (import.meta.env.DEV) {
      console.warn('[Eureka API]', error.message);
    }
    return Promise.reject(error);
  }
);

export default apiClient;

