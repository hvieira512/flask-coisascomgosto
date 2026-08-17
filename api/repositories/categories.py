"""Data access for the categories table."""

from __future__ import annotations

from api.repositories.base import NameTableRepository


class CategoryRepository(NameTableRepository):
    TABLE = "categories"

    def create(self, name: str) -> int:
        self._cursor.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
        return self._cursor.lastrowid

    def update(self, category_id: int, name: str) -> None:
        self._cursor.execute(
            "UPDATE categories SET name = %s WHERE id = %s", (name, category_id)
        )

    def delete(self, category_id: int) -> None:
        """Delete a category and every product filed under it.

        With no foreign keys in the schema this cascade is performed here.
        Products are deleted through ProductRepository so their own images,
        sizes and variants go with them.
        """
        from api.repositories.products import ProductRepository

        self._cursor.execute(
            "SELECT id FROM products WHERE category_id = %s", (category_id,)
        )
        product_ids = [row["id"] for row in self._cursor.fetchall()]

        products = ProductRepository(self._cursor)
        for product_id in product_ids:
            products.delete(product_id)

        self._cursor.execute("DELETE FROM categories WHERE id = %s", (category_id,))
