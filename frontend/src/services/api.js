import axios from 'axios';

const getApiBaseUrl = () => {
    if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
    if (typeof window !== 'undefined' && window.location?.hostname?.includes('onrender.com'))
        return 'https://ai-bank-statement-analyzer.onrender.com/api';
    return 'http://localhost:8000/api';
};

const api = axios.create({
    baseURL: getApiBaseUrl(),
    timeout: 120000,
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    (response) => response,
    (error) => {
        const status = error.response?.status;
        const skipLogout = error.config?.skipAuthRedirect;
        if (status === 401 && !skipLogout) {
            localStorage.removeItem('token');
            window.location.reload();
        }
        return Promise.reject(error);
    }
);

export default api;
