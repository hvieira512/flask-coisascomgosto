import { API } from "../../core/api.js";
import { reference, typeOptions } from "./reference.js";

export const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));

const option = (value, label, selected) =>
    `<option value="${value}"${String(selected) === String(value) ? " selected" : ""}>${escapeHtml(label)}</option>`;

/**
 * The create/edit form. `product` is null when creating.
 *
 * Variants and photographs are managed from the edit modal only: both need a
 * product id, which does not exist until the product is saved.
 */
export async function productForm(product = null) {
    const { categories, types, collections, sizes } = await reference();
    const selectedSizes = new Set((product?.sizes ?? []).map((s) => s.id));

    return `
    <form id="product-form" data-product-id="${product?.id ?? ""}">
      <div class="field">
        <label class="label is-small" for="pf-name">Nome</label>
        <div class="control">
          <input class="input" id="pf-name" name="name" required
                 value="${escapeHtml(product?.name ?? "")}" placeholder="Caixa Redonda Filigrana">
        </div>
      </div>

      <div class="field">
        <label class="label is-small" for="pf-description">Descrição</label>
        <div class="control">
          <textarea class="textarea" id="pf-description" name="description" rows="2"
                    placeholder="Como é a peça, numa linha.">${escapeHtml(product?.description ?? "")}</textarea>
        </div>
      </div>

      <div class="columns is-mobile">
        <div class="column">
          <div class="field">
            <label class="label is-small" for="pf-category">Categoria</label>
            <div class="select is-fullwidth">
              <select id="pf-category" name="category_id" required>
                ${categories.map((c) => option(c.id, c.name, product?.category?.id)).join("")}
              </select>
            </div>
          </div>
        </div>
        <div class="column">
          <div class="field">
            <label class="label is-small" for="pf-type">Tipo</label>
            <div class="select is-fullwidth">
              <select id="pf-type" name="type_id">
                <option value="">—</option>
                ${typeOptions(types).map((t) => option(t.id, t.label, product?.type?.id)).join("")}
              </select>
            </div>
          </div>
        </div>
      </div>

      <div class="field">
        <label class="label is-small" for="pf-collection">Colecção</label>
        <div class="select is-fullwidth">
          <select id="pf-collection" name="collection_id">
            <option value="">—</option>
            ${collections.map((c) => option(c.id, c.name, product?.collection?.id)).join("")}
          </select>
        </div>
      </div>

      <div class="field">
        <label class="label is-small">Tamanhos</label>
        <div class="control" id="pf-sizes">
          ${sizes.map((s) => `
            <label class="checkbox mr-4">
              <input type="checkbox" value="${s.id}"${selectedSizes.has(s.id) ? " checked" : ""}>
              ${escapeHtml(s.name)}
            </label>`).join("")}
        </div>
      </div>

      <p class="help" id="pf-error" hidden></p>
    </form>`;
}

/** Reads the form, writes the product, and returns its id. */
export async function submitProductForm() {
    const form = document.getElementById("product-form");
    const id = form.dataset.productId;
    const value = (name) => form.querySelector(`[name="${name}"]`).value.trim();

    const payload = {
        name: value("name"),
        description: value("description"),
        category_id: Number(value("category_id")),
    };
    // The API rejects an explicit null on these, so they are omitted instead.
    if (value("type_id")) payload.type_id = Number(value("type_id"));
    if (value("collection_id")) payload.collection_id = Number(value("collection_id"));

    if (!payload.name) throw new Error("O nome é obrigatório.");

    const res = await window.Auth.authFetch(
        id ? API.products.update(id) : API.products.create,
        {
            method: id ? "PUT" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        }
    );

    const body = await res.json();
    if (!res.ok) throw new Error(body.message || "Não foi possível guardar.");

    const productId = id || body.id;

    const sizeIds = [...document.querySelectorAll("#pf-sizes input:checked")]
        .map((input) => Number(input.value));
    await window.Auth.authFetch(API.products.sizes(productId), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ size_ids: sizeIds }),
    });

    return productId;
}
