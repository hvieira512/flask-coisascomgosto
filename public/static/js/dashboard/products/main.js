import { API, request } from "../../core/api.js";
import { Notify } from "../../core/notify.js";
import { allImages, removeImage, uploadImage } from "./images.js";
import {
    addVariant, addVariants, removeVariant, variantChoiceStep, variantsPanel,
    wireVariantChoice, wireVariantPhotos,
} from "./variants.js";
import { reference } from "./reference.js";
import { bodyOf, close, confirmDialog, footOf, modal, open, submitting } from "../../core/modal.js";
import { escapeHtml } from "../../core/html.js";
import { fetchProducts } from "./fetch.js";
import { mountFilters } from "./filters.js";
import {
    PRODUCT_STEPS, productForm, submitProductForm, validateIdentity, wireProductForm,
} from "./form.js";
import { stepDialog } from "../../core/steps.js";

const getProduct = (id) =>
    request(API.products.get(id), { fallback: "Produto não encontrado." });

const showVariantsTab = () =>
    bootstrap.Tab.getOrCreateInstance(
        document.querySelector('#edit-tabs [data-tab="variants"] .nav-link')
    ).show();

async function uploadChosenPhotos(productId, picks) {
    const withPhotos = picks.filter((pick) => pick.files.length);
    if (!withPhotos.length) return;

    const product = await getProduct(productId);
    const variantOf = new Map(
        product.variants.map((variant) => [variant.color_set.id, variant.id])
    );

    const failed = [];
    for (const { colorSetId, files } of withPhotos) {
        for (const file of files) {
            try {
                await uploadImage(productId, {
                    file,
                    variantId: variantOf.get(colorSetId),
                    alt: product.name,
                });
            } catch (error) {
                failed.push(error.message);
            }
        }
    }

    if (failed.length) {
        Notify.error(
            `A peça foi criada, mas ${failed.length === 1
                ? "uma fotografia não foi enviada"
                : `${failed.length} fotografias não foram enviadas`}. Tente de novo no separador Cores e fotografias.`
        );
    }
}

async function openCreate() {
    const { colorSets } = await reference();
    let chosenColorSets = () => [];

    stepDialog({
        id: "newProductModal",
        body: (await productForm()) + variantChoiceStep(colorSets),
        titles: [...PRODUCT_STEPS, "Cores"],
        validate: [validateIdentity, validateIdentity, validateIdentity],
        finishLabel: "Criar produto",
        afterRender: (root) => {
            wireProductForm(root);
            chosenColorSets = wireVariantChoice(root);
        },
        onFinish: async (root) => {
            const picks = chosenColorSets();
            const id = await submitProductForm(root);
            await addVariants(id, picks.map((pick) => pick.colorSetId));
            await uploadChosenPhotos(id, picks);
            return id;
        },
        success: "Produto criado.",
        after: async (id) => {
            await mountFilters(fetchProducts).then(fetchProducts);
            await openEdit(id);
            showVariantsTab();
        },
    });
}

async function openEdit(id) {
    const product = await getProduct(id);

    bodyOf("editProductModal").innerHTML = `
        <ul class="nav nav-tabs mb-3" id="edit-tabs" role="tablist">
          <li class="nav-item" role="presentation" data-tab="details">
            <button class="nav-link active" data-bs-toggle="tab" type="button"
                    data-bs-target="#edit-pane-details" role="tab"
                    aria-controls="edit-pane-details" aria-selected="true">Detalhes</button>
          </li>
          <li class="nav-item" role="presentation" data-tab="variants">
            <button class="nav-link" data-bs-toggle="tab" type="button"
                    data-bs-target="#edit-pane-variants" role="tab"
                    aria-controls="edit-pane-variants" aria-selected="false">Cores e fotografias</button>
          </li>
        </ul>
        <div class="tab-content">
          <div class="tab-pane fade show active" id="edit-pane-details" role="tabpanel"
               data-panel="details">${await productForm(product)}</div>
          <div class="tab-pane fade" id="edit-pane-variants" role="tabpanel"
               data-panel="variants">${await variantsPanel(product)}</div>
        </div>`;

    footOf("editProductModal").innerHTML = `
        <button class="btn btn-outline-secondary" data-bs-dismiss="modal">Fechar</button>
        <button class="btn btn-dark" id="edit-submit">Guardar alterações</button>`;

    open("editProductModal");
    wireProductForm(modal("editProductModal"));
    wireEditTabs();
    wireVariantPanel(product);

    document.getElementById("edit-submit").onclick = (event) =>
        submitting(event.currentTarget, async () => {
            await submitProductForm(modal("editProductModal"));
            await close("editProductModal");
            Notify.success("Produto actualizado.");
            await mountFilters(fetchProducts).then(fetchProducts);
        });
}

function wireEditTabs() {
    const root = modal("editProductModal");
    const save = root.querySelector("#edit-submit");

    root.querySelectorAll('#edit-tabs [data-bs-toggle="tab"]').forEach((tab) => {
        tab.addEventListener("shown.bs.tab", () => {
            save.hidden = tab.closest("[data-tab]").dataset.tab !== "details";
        });
    });
}

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
                showVariantsTab();
            });
    }

    document.querySelectorAll("[data-remove-variant]").forEach((button) => {
        button.onclick = async () => {
            const removing = product.variants.find(
                (variant) => String(variant.id) === button.dataset.removeVariant
            );
            const photos = removing?.images?.length ?? 0;

            const confirmed = await Notify.confirm("Remover esta cor?", {
                text: photos
                    ? `${photos} ${photos === 1 ? "fotografia desta cor" : "fotografias desta cor"} também ${photos === 1 ? "desaparece" : "desaparecem"}.`
                    : "",
                danger: true,
                confirmText: "Remover",
            });
            if (!confirmed) return;

            try {
                await removeVariant(product.id, button.dataset.removeVariant);
                Notify.success("Cor removida.");
                await refreshEdit(product.id);
                showVariantsTab();
            } catch (error) {
                Notify.error(error.message);
            }
        };
    });

    wireVariantPhotos(product, {
        onUpload: async (variant, files) => {
            for (const file of files) {
                await uploadImage(product.id, {
                    file,
                    variantId: variant.id,
                    alt: product.name,
                });
            }
            Notify.success(files.length === 1 ? "Fotografia adicionada." : "Fotografias adicionadas.");
            await refreshEdit(product.id);
            showVariantsTab();
        },
        onRemove: async (image) => {
            const confirmed = await Notify.confirm("Remover esta fotografia?", {
                danger: true,
                confirmText: "Remover",
            });
            if (!confirmed) throw new Error("");

            await removeImage(product.id, image.id);
            Notify.success("Fotografia removida.");
            await refreshEdit(product.id);
            showVariantsTab();
        },
    });
}

async function openDelete(id) {
    const product = await getProduct(id);

    confirmDialog({
        id: "deleteProductModal",
        body: `
            <p>Apagar <strong>${escapeHtml(product.name)}</strong>?</p>
            <p class="text-body-secondary fs-7 mt-2">
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

    const row = event.target.closest("#product-list tr[data-product-id]");
    if (row) openEdit(row.dataset.productId);
});

document.getElementById("new-product")?.addEventListener("click", openCreate);

mountFilters(fetchProducts).then(fetchProducts);
