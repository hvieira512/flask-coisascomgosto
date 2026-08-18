import { API, request } from "../../core/api.js";
import { escapeHtml } from "../../core/html.js";
import { reference, typeOptions } from "./reference.js";

const option = (value, label, selected) =>
    `<option value="${value}"${String(selected) === String(value) ? " selected" : ""}>${escapeHtml(label)}</option>`;

/** What the two field groups are called, in order. */
export const PRODUCT_STEPS = ["A peça", "Detalhes"];

/**
 * The create/edit form. `product` is null when creating.
 *
 * The fields come in two `data-step` groups: what the piece is, which is all the
 * API requires, and then everything optional. core/steps.js shows one at a time
 * when creating; the edit modal leaves both visible, since editing is changing
 * one thing rather than answering a sequence.
 *
 * Variants and photographs are in neither group — both need a product id, which
 * does not exist until this form is saved.
 */
export async function productForm(product = null) {
    const { materials, types, collections, sizes } = await reference();
    const selectedSizes = new Set((product?.sizes ?? []).map((s) => s.id));

    return `
    <form id="product-form" data-product-id="${product?.id ?? ""}">
      <div data-step="identity">
        <div class="field">
          <label class="label is-small" for="pf-name">Nome</label>
          <div class="control">
            <input class="input" id="pf-name" name="name" required
                   value="${escapeHtml(product?.name ?? "")}" placeholder="Caixa Redonda Filigrana">
          </div>
        </div>

        <div class="field">
          <label class="label is-small" for="pf-type">Tipo</label>
          <div class="select is-fullwidth">
            <select id="pf-type" name="type_id" required>
              <option value="">Escolher…</option>
              ${typeOptions(types).map((t) => option(t.id, t.label, product?.type?.id)).join("")}
            </select>
          </div>
          <p class="help">A família da peça — Caixa, Moldura, Coração.</p>
        </div>
      </div>

      <div data-step="details">
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
              <label class="label is-small" for="pf-material">Material</label>
              <div class="select is-fullwidth">
                <select id="pf-material" name="material_id">
                  <option value="">—</option>
                  ${materials.map((m) => option(m.id, m.name, product?.material?.id)).join("")}
                </select>
              </div>
            </div>
          </div>
          <div class="column">
            <div class="field">
              <label class="label is-small" for="pf-collection">Colecção</label>
              <div class="select is-fullwidth">
                <select id="pf-collection" name="collection_id">
                  <option value="">—</option>
                  ${collections.map((c) => option(c.id, c.name, product?.collection?.id)).join("")}
                </select>
              </div>
            </div>
          </div>
        </div>

        <div class="field mb-0">
          <label class="label is-small">Tamanhos</label>
          <div class="control" id="pf-sizes">
            ${sizes.map((s) => `
              <label class="checkbox mr-4">
                <input type="checkbox" value="${s.id}"${selectedSizes.has(s.id) ? " checked" : ""}>
                ${escapeHtml(s.name)}
              </label>`).join("")}
          </div>
          <p class="help">Deixe vazio se a peça só se faz num tamanho.</p>
        </div>
      </div>
    </form>`;
}

/** The first step's own check, run before it will let go. */
export function validateIdentity(root) {
    const form = root.querySelector("#product-form");
    if (!form.querySelector('[name="name"]').value.trim()) {
        throw new Error("O nome é obrigatório.");
    }
    if (!form.querySelector('[name="type_id"]').value) {
        throw new Error("O tipo é obrigatório.");
    }
}

/**
 * Reads the form, writes the product, and returns its id.
 *
 * `root` scopes the lookup to one modal: the create and edit modals both hold a
 * form with the same ids, and the closed one stays in the DOM.
 */
export async function submitProductForm(root = document) {
    const form = root.querySelector("#product-form");
    const id = form.dataset.productId;
    const value = (name) => form.querySelector(`[name="${name}"]`).value.trim();

    const payload = {
        name: value("name"),
        description: value("description"),
        type_id: Number(value("type_id")),
    };
    // The API rejects an explicit null on these, so they are omitted instead.
    if (value("material_id")) payload.material_id = Number(value("material_id"));
    if (value("collection_id")) payload.collection_id = Number(value("collection_id"));

    if (!payload.name) throw new Error("O nome é obrigatório.");
    if (!payload.type_id) throw new Error("O tipo é obrigatório.");

    const saved = await request(id ? API.products.update(id) : API.products.create, {
        method: id ? "PUT" : "POST",
        body: payload,
        fallback: "Não foi possível guardar.",
    });

    const productId = id || saved.id;

    const sizeIds = [...root.querySelectorAll("#pf-sizes input:checked")]
        .map((input) => Number(input.value));
    await request(API.products.sizes(productId), {
        method: "PUT",
        body: { size_ids: sizeIds },
        fallback: "Não foi possível guardar os tamanhos.",
    });

    return productId;
}
