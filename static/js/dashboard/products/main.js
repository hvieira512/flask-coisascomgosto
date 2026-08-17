import { API } from "../../core/api.js";
import { bodyOf, close, footOf, modal, open, submitting } from "../../core/modal.js";
import { fetchProducts } from "./fetch.js";
import { mountFilters } from "./filters.js";
import { productForm, submitProductForm } from "./form.js";
import { addImage, allImages, imagesPanel, removeImage, uploadImage } from "./images.js";
import { addVariant, removeVariant, variantsPanel } from "./variants.js";

const getProduct = async (id) => {
    const res = await fetch(API.products.get(id));
    if (!res.ok) throw new Error("Produto não encontrado.");
    return res.json();
};

async function openCreate() {
    bodyOf("newProductModal").innerHTML = await productForm();
    footOf("newProductModal").innerHTML = `
        <button class="button" data-modal-close>Cancelar</button>
        <button class="button is-dark" id="create-submit">Criar produto</button>`;
    open("newProductModal");

    document.getElementById("create-submit").onclick = (event) =>
        submitting(event.currentTarget, async () => {
            const id = await submitProductForm(modal("newProductModal"));
            close("newProductModal");
            Notify.success("Produto criado.");
            await mountFilters(fetchProducts).then(fetchProducts);
            openEdit(id);   // straight on to colours and photographs
        });
}

async function openEdit(id) {
    const product = await getProduct(id);

    bodyOf("editProductModal").innerHTML = `
        <div class="tabs is-small is-boxed mb-4" id="edit-tabs">
          <ul>
            <li class="is-active" data-tab="details"><a>Detalhes</a></li>
            <li data-tab="variants"><a>Cores</a></li>
            <li data-tab="images"><a>Fotografias</a></li>
          </ul>
        </div>
        <div data-panel="details">${await productForm(product)}</div>
        <div data-panel="variants" hidden>${await variantsPanel(product)}</div>
        <div data-panel="images" hidden>${imagesPanel(product)}</div>`;

    footOf("editProductModal").innerHTML = `
        <button class="button" data-modal-close>Fechar</button>
        <button class="button is-dark" id="edit-submit">Guardar alterações</button>`;

    open("editProductModal");
    wireEditTabs();
    wireVariantPanel(product);
    wireImagePanel(product);

    document.getElementById("edit-submit").onclick = (event) =>
        submitting(event.currentTarget, async () => {
            await submitProductForm(modal("editProductModal"));
            close("editProductModal");
            Notify.success("Produto actualizado.");
            await mountFilters(fetchProducts).then(fetchProducts);
        });
}

function wireEditTabs() {
    const root = modal("editProductModal");
    const tabs = root.querySelector("#edit-tabs");
    tabs.querySelectorAll("li").forEach((tab) => {
        tab.onclick = () => {
            tabs.querySelectorAll("li").forEach((t) => t.classList.remove("is-active"));
            tab.classList.add("is-active");
            root.querySelectorAll("[data-panel]").forEach((panel) => {
                panel.hidden = panel.dataset.panel !== tab.dataset.tab;
            });
        };
    });
}

/** Re-opens the modal on the same product so every panel sees fresh data. */
async function refreshEdit(productId) {
    await mountFilters(fetchProducts).then(fetchProducts);
    await openEdit(productId);
}

function wireVariantPanel(product) {
    const add = document.getElementById("add-variant");
    if (add) {
        add.onclick = (event) =>
            submitting(event.currentTarget, async () => {
                await addVariant(product.id, document.getElementById("variant-picker").value);
                Notify.success("Cor adicionada.");
                await refreshEdit(product.id);
                document.querySelector('#edit-tabs [data-tab="variants"]').click();
            });
    }

    document.querySelectorAll("[data-remove-variant]").forEach((button) => {
        button.onclick = async () => {
            if (!(await Notify.confirm("Remover esta cor?", { danger: true, confirmText: "Remover" }))) return;
            try {
                await removeVariant(product.id, button.dataset.removeVariant);
                Notify.success("Cor removida.");
                await refreshEdit(product.id);
                document.querySelector('#edit-tabs [data-tab="variants"]').click();
            } catch (error) {
                Notify.error(error.message);
            }
        };
    });
}

function wireImagePanel(product) {
    const picker = document.getElementById("image-file");
    if (picker) {
        picker.onchange = () => {
            document.getElementById("image-file-name").textContent =
                picker.files[0]?.name ?? "Nenhum ficheiro";
        };
    }

    const add = document.getElementById("add-image");
    if (add) {
        add.onclick = (event) =>
            submitting(event.currentTarget, async () => {
                const file = document.getElementById("image-file").files[0];
                const variantId = document.getElementById("image-variant").value;

                if (file) {
                    await uploadImage(product.id, { file, variantId, alt: product.name });
                } else {
                    await addImage(product.id, {
                        url: document.getElementById("image-url").value.trim(),
                        variantId,
                        alt: product.name,
                    });
                }
                Notify.success("Fotografia adicionada.");
                await refreshEdit(product.id);
                document.querySelector('#edit-tabs [data-tab="images"]').click();
            });
    }

    document.querySelectorAll("[data-remove-image]").forEach((button) => {
        button.onclick = async () => {
            if (!(await Notify.confirm("Remover esta fotografia?", { danger: true, confirmText: "Remover" }))) return;
            try {
                await removeImage(product.id, button.dataset.removeImage);
                Notify.success("Fotografia removida.");
                await refreshEdit(product.id);
                document.querySelector('#edit-tabs [data-tab="images"]').click();
            } catch (error) {
                Notify.error(error.message);
            }
        };
    });
}

async function openView(id) {
    const product = await getProduct(id);
    const image = product.primary_image
        ? `<img src="${escapeHtml(product.primary_image.url)}" alt="${escapeHtml(product.name)}" class="dash-view-image">`
        : window.ProductPlaceholder.markup(product);

    bodyOf("viewProductModal").innerHTML = `
        <div class="dash-view">
          <div>${image}</div>
          <div>
            <h3 class="title is-5 mb-2">${escapeHtml(product.name)}</h3>
            <p class="has-text-grey mb-4">${escapeHtml(product.description ?? "")}</p>
            <dl class="dash-facts">
              <dt>Categoria</dt><dd>${escapeHtml(product.category.name)}</dd>
              <dt>Tipo</dt><dd>${escapeHtml(product.type?.name ?? "—")}</dd>
              <dt>Colecção</dt><dd>${escapeHtml(product.collection?.name ?? "—")}</dd>
              <dt>Tamanhos</dt><dd>${product.sizes.map((s) => escapeHtml(s.name)).join(", ") || "—"}</dd>
            </dl>
            <div class="mt-4">${product.variants.map((v) => window.ColorSet.badge(v.color_set)).join(" ")}</div>
          </div>
        </div>`;
    footOf("viewProductModal").innerHTML =
        `<button class="button" data-modal-close>Fechar</button>`;
    open("viewProductModal");
}

async function openDelete(id) {
    const product = await getProduct(id);

    bodyOf("deleteProductModal").innerHTML = `
        <p>Apagar <strong>${escapeHtml(product.name)}</strong>?</p>
        <p class="has-text-grey is-size-7 mt-2">
          Remove também as suas ${product.variants.length} cores e
          ${allImages(product).length} fotografias. Não pode ser anulado.
        </p>`;
    footOf("deleteProductModal").innerHTML = `
        <button class="button" data-modal-close>Cancelar</button>
        <button class="button is-danger" id="delete-submit">Apagar</button>`;
    open("deleteProductModal");

    document.getElementById("delete-submit").onclick = (event) =>
        submitting(event.currentTarget, async () => {
            const res = await fetch(API.products.delete(id), { method: "DELETE" });
            if (!res.ok) throw new Error("Não foi possível apagar.");
            close("deleteProductModal");
            Notify.success("Produto apagado.");
            await mountFilters(fetchProducts).then(fetchProducts);
        });
}

document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-product-action]");
    if (trigger) {
        const { productAction: action, productId: id } = trigger.dataset;
        if (action === "view") openView(id);
        if (action === "edit") openEdit(id);
        if (action === "delete") openDelete(id);
        return;
    }

    // The whole row opens the piece for editing, which is what the pointer
    // cursor on it promises. Checked after the buttons so their own actions win.
    const row = event.target.closest("#product-list tr[data-product-id]");
    if (row) openEdit(row.dataset.productId);
});

document.getElementById("new-product")?.addEventListener("click", openCreate);

mountFilters(fetchProducts).then(fetchProducts);
