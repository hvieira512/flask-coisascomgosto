import { get, post } from "./utils.js";

const BASE = "/api/auth";

export const login = async (data) => post(`${BASE}/login`, data);

export const register = async (data) => post(`${BASE}/register`, data);

export const logout = async () => post(`${BASE}/logout`);

export const getSession = async () => get(`${BASE}/session`);
