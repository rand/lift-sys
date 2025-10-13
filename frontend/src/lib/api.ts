import axios from "axios";

const baseURL =
  (import.meta.env && (import.meta.env.VITE_API_BASE_URL as string | undefined)) ||
  "";

export const api = axios.create({
  baseURL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});
