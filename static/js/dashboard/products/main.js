import { API, request } from "../../core/api.js";
import { Notify } from "../../core/notify.js";
import { addImage, allImages, imagesPanel, removeImage, uploadImage } from "./images.js";
import { addVariant, removeVariant, variantsPanel } from "./variants.js";
import { bodyOf, close, confirmDialog, footOf, modal, open, submitting } from "../../core/modal.js";
import { escapeHtml } from "../../core/html.js";
import { fetchProducts } from "./fetch.js";
import { mountFilters } from "./filters.js";
import { PRODUCT_STEPS, productForm, submitProductForm, validateIdentity } from "./form.js";
import { stepDialog } from "../../core/steps.js";

const getProduct = (id) =>
    request(API.products.get(id), { fallback: "Produto não encontrado." });

/**
 * Creating asks what the piece is, then the optional details, and writes once at
 * the end — a piece is on the storefront the moment its row exists, so a
 * half-answered form must not create one.
 *
 * Colours and photographs cannot be steps here: both need an id. The save hands
 * straight over to the edit modal on its Cores tab, which is where the work
 * continues.
 */
async function openCreate() {
    stepDialog({
        id: "newProductModal",
        body: await productForm(),
        titles: PRODUCT_STEPS,
        validate: [validateIdentity, validateIdentity],
        finishLabel: "Criar produto",
        onFinish: (root) => submitProductForm(root),
        success: "Produto criado.",
        after: async (id) => {
            await mountFilters(fetchProducts).then(fetchProducts);
            await openEdit(id);
            document.querySelector('#edit-tabs [data-tab="variants"]').click();
        },
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
    // Only the details form has pending changes to save: colours and
    // photographs are written the moment they are added or removed, so leaving
    // "Guardar alterações" on those tabs promised a save that never happened —
    // and reported "Produto actualizado" for a form nobody had touched.
    const save = root.querySelector("#edit-submit");

    tabs.querySelectorAll("li").forEach((tab) => {
        tab.onclick = () => {
            tabs.querySelectorAll("li").forEach((t) => t.classList.remove("is-active"));
            tab.classList.add("is-active");
            root.querySelectorAll("[data-panel]").forEach((panel) => {
                panel.hidden = panel.dataset.panel !== tab.dataset.tab;
            });
            // Bulma's .button is display:inline-flex, which outranks the
            // [hidden] attribute — is-hidden carries the !important.
            save.classList.toggle("is-hidden", tab.dataset.tab !== "details");
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

async function openDelete(id) {
    const product = await getProduct(id);

    confirmDialog({
        id: "deleteProductModal",
        body: `
            <p>Apagar <strong>${escapeHtml(product.name)}</strong>?</p>
            <p class="has-text-grey is-size-7 mt-2">
              Remove também as suas ${product.variants.length} cores e
              ${allImages(product).length} fotografias. Não pode ser anulado.
            </p>`,
        onConfirm: () => request(API.products.delete(id),
                               { method: "DELETE", fallback: "Não foi possível apagar." }),
        success: "Produto apagado.",
        after: () => mountFilters(fetchProducts).then(fetchProducts),
    });
}

document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-product-action]");
    if (trigger) {
        const { productAction: action, productId: id } = trigger.dataset;
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
