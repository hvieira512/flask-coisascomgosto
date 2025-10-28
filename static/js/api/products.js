import { get, put, post, del } from "./utils.js";

const BASE = "/api/products";

export const getProducts = async (params = {}) => get(BASE, params);

export const getProduct = async (id) => get(`${BASE}/${id}`);

export const createProduct = async (payload) => post(BASE, payload);

export const updateProduct = async (id, payload) =>
    put(`${BASE}/${id}`, payload);

export const deleteProduct = async (id) => del(`${BASE}/${id}`);
