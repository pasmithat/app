import axios from "axios";

export const api = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api/power` });

export const errMsg = (e) => e?.response?.data?.detail || e?.message || "Request failed";
