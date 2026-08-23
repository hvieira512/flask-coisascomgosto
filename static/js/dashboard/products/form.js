import { API, request } from "../../core/api.js";
import { escapeHtml, fieldIcon } from "../../core/html.js";
import { reference, typeOptions } from "./reference.js";

const option = (value, label, selected) =>
    `<option value="${value}"${String(selected) === String(value) ? " selected" : ""}>${escapeHtml(label)}</option>`;

const materialChip = (material, chosen) => `
  <button type="button" data-material-id="${material.id}" aria-pressed="${chosen}"
          class="badge rounded-pill chip is-quiet collection-chip${chosen ? " is-active" : ""}">
    ${escapeHtml(material.name)}
  </button>`;

// Delegated on the document because this form is mounted from two places — the
// new-piece wizard and the edit panels — and neither needs to know about it.
document.addEventListener("click", (event) => {
    const chip = event.target.closest("#pf-materials .collection-chip");
    if (!chip) return;

    const on = chip.getAttribute("aria-pressed") !== "true";
    chip.setAttribute("aria-pressed", String(on));
    chip.classList.toggle("is-active", on);
});

export const PRODUCT_STEPS = ["A peça", "Detalhes"];

export async function productForm(product = null) {
    const { materials, types, collections, sizes } = await reference();
    const selectedSizes = new Set((product?.sizes ?? []).map((s) => s.id));
    const chosenMaterials = new Set((product?.materials ?? []).map((m) => m.id));

    return `
    <form id="product-form" data-product-id="${product?.id ?? ""}">
      <div data-step="identity">
        <div class="mb-3">
          <label class="form-label fs-7" for="pf-name">Nome</label>
          <div class="input-group">
            <input class="form-control" id="pf-name" name="name" required
                   value="${escapeHtml(product?.name ?? "")}" placeholder="Caixa Redonda Filigrana">
            ${fieldIcon("fa-solid fa-tag")}
          </div>
        </div>

        <div class="mb-3">
          <label class="form-label fs-7" for="pf-type">Tipo</label>
          <div class="input-group">
            <select class="form-select" id="pf-type" name="type_id" required>
              <option value="">Escolher…</option>
              ${typeOptions(types).map((t) => option(t.id, t.label, product?.type?.id)).join("")}
            </select>
            ${fieldIcon("fa-solid fa-shapes")}
          </div>
          <p class="help mb-0">A família da peça — Caixa, Moldura, Coração.</p>
        </div>
      </div>

      <div data-step="details">
        <div class="mb-3">
          <label class="form-label fs-7" for="pf-description">Descrição</label>
          <textarea class="form-control" id="pf-description" name="description" rows="2"
                    placeholder="Como é a peça, numa linha.">${escapeHtml(product?.description ?? "")}</textarea>
        </div>

        <div class="mb-3">
          <label class="form-label fs-7">De que é feita</label>
          <div class="d-flex flex-wrap gap-1" id="pf-materials">
            ${materials.map((m) => materialChip(m, chosenMaterials.has(m.id))).join("")}
          </div>
          <p class="help mb-0">Quase sempre uma só. Escolha mais do que uma quando a
            peça as junta — uma base de madeira com um boneco de pasta de modelar.</p>
        </div>

        <div class="row g-3 mb-3">
          <div class="col">
            <label class="form-label fs-7" for="pf-collection">Colecção</label>
            <div class="input-group">
              <select class="form-select" id="pf-collection" name="collection_id">
                <option value="">—</option>
                ${collections.map((c) => option(c.id, c.name, product?.collection?.id)).join("")}
              </select>
              ${fieldIcon("fa-solid fa-layer-group")}
            </div>
          </div>
        </div>

        <div>
          <label class="form-label fs-7">Tamanhos</label>
          <div id="pf-sizes">
            ${sizes.map((s) => `
              <div class="form-check form-check-inline">
                <input class="form-check-input" type="checkbox" id="pf-size-${s.id}"
                       value="${s.id}"${selectedSizes.has(s.id) ? " checked" : ""}>
                <label class="form-check-label" for="pf-size-${s.id}">${escapeHtml(s.name)}</label>
              </div>`).join("")}
          </div>
          <p class="help mb-0">Deixe vazio se a peça só se faz num tamanho.</p>
        </div>
      </div>
    </form>`;
}

export function validateIdentity(root) {
    const form = root.querySelector("#product-form");
    if (!form.querySelector('[name="name"]').value.trim()) {
        throw new Error("O nome é obrigatório.");
    }
    if (!form.querySelector('[name="type_id"]').value) {
        throw new Error("O tipo é obrigatório.");
    }
}

export async function submitProductForm(root = document) {
    const form = root.querySelector("#product-form");
    const id = form.dataset.productId;
    const value = (name) => form.querySelector(`[name="${name}"]`).value.trim();

    const payload = {
        name: value("name"),
        description: value("description"),
        type_id: Number(value("type_id")),
        // Always sent, empty included: this replaces what the piece was made of,
        // so unpressing every chip has to mean "unclassified" rather than
        // "leave it alone".
        material_ids: [...root.querySelectorAll('#pf-materials [aria-pressed="true"]')]
            .map((chip) => Number(chip.dataset.materialId)),
    };
    if (value("collection_id")) payload.collection_id = Number(value("collection_id"));

    if (!payload.name) throw new Error("O nome é obrigatório.");
    if (!payload.type_id) throw new Error("O tipo é obrigatório.");

    const saved = await request(id ? API.products.update(id) : API.products.create, {
        method: id ? "PUT" : "POST",
        body: payload,
        fallback: "Não foi possível guardar.",
    });

    const productId = id || saved.id;

    form.dataset.productId = productId;

    const sizeIds = [...root.querySelectorAll("#pf-sizes input:checked")]
        .map((input) => Number(input.value));
    await request(API.products.sizes(productId), {
        method: "PUT",
        body: { size_ids: sizeIds },
        fallback: "Não foi possível guardar os tamanhos.",
    });

    return productId;
}
