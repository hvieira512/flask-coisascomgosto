import { API, fetchData } from "../core/api.js"

const loadCategories = async () => {
    const categories = await fetchData(API.categories.list);
    console.log(categories);
}

loadCategories();
