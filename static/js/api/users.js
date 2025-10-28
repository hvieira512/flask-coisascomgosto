import { get, put, post, del } from "./utils.js";

const BASE = "/api/users";

export const getUsers = async (params = {}) => get(BASE, params);

export const getUser = async (id) => get(`${BASE}/${id}`);

export const createUser = async (payload) => post(BASE, payload);

export const updateUser = async (id, payload) => put(`${BASE}/${id}`, payload);

export const deleteUser = async (id) => del(`${BASE}/${id}`);
