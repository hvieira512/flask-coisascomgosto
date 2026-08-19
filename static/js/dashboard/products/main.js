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
import { PRODUCT_STEPS, productForm, submitProductForm, validateIdentity } from "./form.js";
import { stepDialog } from "../../core/steps.js";

const getProduct = (id) =>
    request(API.products.get(id), { fallback: "Produto não encontrado." });

/**
 * Creating asks what the piece is, then the optional details, then the colours it
 * is offered in — and writes once at the end. A piece is on the storefront the
 * moment its row exists, so a half-answered form must not create one.
 *
 * The colours are chosen here but attached afterwards, because a variant needs a
 * product id. Photographs are the one thing that cannot be chosen in advance at
 * all: they need both an id and a file, so the save hands over to the edit modal on
 * its Fotografias tab, which is where the work continues.
 */
/**
 * Sends the photographs the wizard collected, each against the variant it belongs
 * to. The variant ids only exist now, so they are read back off the saved piece
 * rather than guessed from the order they were posted in.
 *
 * A failed photograph does not fail the save. The piece and its colours are already
 * written, and a retry would upload the ones that did work a second time — so this
 * reports what did not arrive and lets the Fotografias tab, which the wizard is
 * about to open, be where it is tried again.
 */
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
        afterRender: (root) => { chosenColorSets = wireVariantChoice(root); },
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
            // Where the colours and their photographs now live, which is what is left
            // to do for a piece that has just been created.
            document.querySelector('#edit-tabs [data-tab="variants"]').click();
        },
    });
}

async function openEdit(id) {
    const product = await getProduct(id);

    // Two tabs, not three: every photograph belongs to a colour, so Cores holds the
    // colours and each colour's photographs together. Fotografias was the same
    // information asked for a second time, through a dropdown naming the colour.
    bodyOf("editProductModal").innerHTML = `
        <div class="tabs is-small is-boxed mb-4" id="edit-tabs">
          <ul>
            <li class="is-active" data-tab="details"><a>Detalhes</a></li>
            <li data-tab="variants"><a>Cores e fotografias</a></li>
          </ul>
        </div>
        <div data-panel="details">${await productForm(product)}</div>
        <div data-panel="variants" hidden>${await variantsPanel(product)}</div>`;

    footOf("editProductModal").innerHTML = `
        <button class="button" data-modal-close>Fechar</button>
        <button class="button is-dark" id="edit-submit">Guardar alterações</button>`;

    open("editProductModal");
    wireEditTabs();
    wireVariantPanel(product);

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
            const removing = product.variants.find(
                (variant) => String(variant.id) === button.dataset.removeVariant
            );
            const photos = removing?.images?.length ?? 0;

            // The colour's photographs go with it, and there is no undo, so the number
            // is on the question rather than discovered afterwards.
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
                document.querySelector('#edit-tabs [data-tab="variants"]').click();
            } catch (error) {
                Notify.error(error.message);
            }
        };
    });

    // The seeded photographs that belong to no colour, which can only be removed.
    document.querySelectorAll("[data-remove-image]").forEach((button) => {
        button.onclick = async () => {
            if (!(await Notify.confirm("Remover esta fotografia?", {
                danger: true, confirmText: "Remover",
            }))) return;

            try {
                await removeImage(product.id, button.dataset.removeImage);
                Notify.success("Fotografia removida.");
                await refreshEdit(product.id);
                document.querySelector('#edit-tabs [data-tab="variants"]').click();
            } catch (error) {
                Notify.error(error.message);
            }
        };
    });

    // A tray per colour. The piece exists here, so a photograph is uploaded the moment
    // it is chosen and the panel is rebuilt from what the server then has.
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
            document.querySelector('#edit-tabs [data-tab="variants"]').click();
        },
        onRemove: async (image) => {
            const confirmed = await Notify.confirm("Remover esta fotografia?", {
                danger: true,
                confirmText: "Remover",
            });
            // Throwing is how the picker is told to keep the photograph it is showing.
            if (!confirmed) throw new Error("");

            await removeImage(product.id, image.id);
            Notify.success("Fotografia removida.");
            await refreshEdit(product.id);
            document.querySelector('#edit-tabs [data-tab="variants"]').click();
        },
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
