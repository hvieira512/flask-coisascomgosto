import { API, request } from "../../core/api.js";
import { escapeHtml } from "../../core/html.js";
import { picked, pickChip, wirePicks } from "../picks.js";
import { reference, typeOptions } from "./reference.js";

const option = (value, label, selected) =>
    `<option value="${value}"${String(selected) === String(value) ? " selected" : ""}>${escapeHtml(label)}</option>`;

/* A collection gathers colour sets, so a piece is in one because one of its
   colourways is — never because this form said so. The field used to be here and
   wrote a second, unsynchronised answer; now the form reports what the colours
   already say and points at where it is decided. */
const collectionsNote = (product) => {
    const names = (product.collections ?? []).map((c) => c.name);

    return `
      <div class="mb-3">
        <label class="form-label fs-7">Colecções</label>
        <p class="mb-1">${names.length
            ? names.map((name) => escapeHtml(name)).join(" · ")
            : "<span class=\"text-body-secondary\">Em nenhuma</span>"}</p>
        <p class="help mb-0">Vem das cores desta peça: uma colecção reúne
          conjuntos de cor. Muda-se em <a href="/dashboard/colors">Cores</a>,
          no conjunto.</p>
      </div>`;
};

export const PRODUCT_STEPS = ["A peça", "Detalhes"];

export async function productForm(product = null) {
    const { materials, types, sizes } = await reference();
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
          </div>
        </div>

        <div class="mb-3">
          <label class="form-label fs-7" for="pf-type">Tipo</label>
          <div class="input-group">
            <select class="form-select" id="pf-type" name="type_id" required>
              <option value="">Escolher…</option>
              ${typeOptions(types).map((t) => option(t.id, t.label, product?.type?.id)).join("")}
            </select>
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
            ${materials.map((m) => pickChip(m.id, m.name, chosenMaterials.has(m.id))).join("")}
          </div>
          <p class="help mb-0">Quase sempre uma só. Escolha mais do que uma quando a
            peça as junta — uma base de madeira com um boneco de pasta de modelar.</p>
        </div>

        ${product ? collectionsNote(product) : ""}

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

/** Call after the form is in the DOM: it is mounted from the new-piece wizard and
 *  from the edit panels, and neither knows what is inside it. */
export function wireProductForm(root) {
    wirePicks(root.querySelector("#pf-materials"));
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
        material_ids: picked(root.querySelector("#pf-materials")),
    };

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
