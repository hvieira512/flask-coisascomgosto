import { get, put, post, del } from "./utils.js";

const BASE = "/api/categories";

export const getCategories = async (params = {}) => get(BASE, params);

export const getCategory = async (id) => get(`${BASE}/${id}`);

export const createCategory = async (payload) => post(BASE, payload);

export const updateCategory = async (id, payload) =>
    put(`${BASE}/${id}`, payload);

export const deleteCategory = async (id) => del(`${BASE}/${id}`);
