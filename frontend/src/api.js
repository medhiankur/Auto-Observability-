import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
    "Accept": "application/json",
  },
  // Don't send credentials in development
  withCredentials: false,
});

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      console.error("API Error Response:", error.response.data);
    } else if (error.request) {
      // Request was made but no response received
      console.error("API No Response:", error.request);
    } else {
      // Error setting up the request
      console.error("API Request Error:", error.message);
    }
    return Promise.reject(error);
  }
);

export default api;
