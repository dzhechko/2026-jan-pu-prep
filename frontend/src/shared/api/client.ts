import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useUserStore } from '@/entities/user/store';

export interface ApiError {
  message: string;
  code: string;
  status: number;
  details?: Record<string, unknown>;
}

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 15_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach JWT token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useUserStore.getState().token;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error),
);

// Response interceptor: handle 401 and transform errors
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ message?: string; code?: string; details?: Record<string, unknown> }>) => {
    if (error.response?.status === 401) {
      useUserStore.getState().clearAuth();
      // In a Telegram Mini App context, we re-authenticate via initData
      // rather than redirecting to a login page
      window.location.hash = '#/';
    }

    const apiError: ApiError = {
      message: error.response?.data?.message || error.message || 'An unexpected error occurred',
      code: error.response?.data?.code || 'UNKNOWN_ERROR',
      status: error.response?.status || 0,
      details: error.response?.data?.details,
    };

    return Promise.reject(apiError);
  },
);

export { apiClient };
