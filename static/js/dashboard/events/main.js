import { API } from "../../core/api.js";
import { bodyOf, close, footOf, modal, open, submitting } from "../../core/modal.js";

const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));

/** "7 – 23 Ago 2026", or a single day. */
function dateRange(event) {
    const format = (iso) =>
        new Date(`${iso}T00:00:00`).toLocaleDateString("pt-PT",
            { day: "numeric", month: "short", year: "numeric" });

    if (!event.ends_on || event.ends_on === event.starts_on) {
        return format(event.starts_on);
    }
    return `${format(event.starts_on)} – ${format(event.ends_on)}`;
}

async function loadEvents() {
    const res = await fetch(`${API.events.list}?limit=100`);
    if (!res.ok) {
        Notify.error("Erro ao buscar eventos.");
        return;
    }

    const { events } = await res.json();
    const rows = document.getElementById("event-rows");

    rows.innerHTML = events.length
        ? events.map((event) => `
            <tr>
              <td>
                <strong>${escapeHtml(event.name)}</strong>
                ${event.description
                    ? `<p class="is-size-7 has-text-grey">${escapeHtml(event.description)}</p>`
                    : ""}
              </td>
              <td class="is-size-7">${escapeHtml(event.location ?? "—")}</td>
              <td class="is-size-7">${escapeHtml(dateRange(event))}</td>
              <td class="has-text-right">
                <button class="button is-small is-ghost" data-event-action="edit"
                        data-event-id="${event.id}" title="Editar">
                  <span class="icon"><i class="fa-solid fa-pencil"></i></span>
                </button>
                <button class="button is-small is-ghost has-text-danger"
                        data-event-action="delete" data-event-id="${event.id}" title="Apagar">
                  <span class="icon"><i class="fa-solid fa-trash"></i></span>
                </button>
              </td>
            </tr>`).join("")
        : `<tr><td colspan="4" class="has-text-centered has-text-grey py-6">
             Ainda não há eventos.</td></tr>`;

    document.getElementById("event-count").textContent =
        `${events.length} ${events.length === 1 ? "evento" : "eventos"}`;
}

function eventForm(event = null) {
    return `
    <form id="event-form" data-event-id="${event?.id ?? ""}">
      <div class="field">
        <label class="label is-small" for="ef-name">Nome</label>
        <input class="input" id="ef-name" name="name" required
               value="${escapeHtml(event?.name ?? "")}"
               placeholder="Feira de Artesanato da Romaria d'Agonia">
      </div>

      <div class="field">
        <label class="label is-small" for="ef-location">Local</label>
        <input class="input" id="ef-location" name="location"
               value="${escapeHtml(event?.location ?? "")}"
               placeholder="Jardim Público, Viana do Castelo">
      </div>

      <div class="columns is-mobile">
        <div class="column">
          <div class="field">
            <label class="label is-small" for="ef-starts">Início</label>
            <input class="input" id="ef-starts" name="starts_on" type="date" required
                   value="${escapeHtml(event?.starts_on ?? "")}">
          </div>
        </div>
        <div class="column">
          <div class="field">
            <label class="label is-small" for="ef-ends">Fim</label>
            <input class="input" id="ef-ends" name="ends_on" type="date"
                   value="${escapeHtml(event?.ends_on ?? "")}">
            <p class="help">Deixe vazio se for de um só dia.</p>
          </div>
        </div>
      </div>

      <div class="field">
        <label class="label is-small" for="ef-description">Descrição</label>
        <textarea class="textarea" id="ef-description" name="description" rows="2"
                  >${escapeHtml(event?.description ?? "")}</textarea>
      </div>

      <div class="field">
        <label class="label is-small" for="ef-url">Ligação</label>
        <input class="input" id="ef-url" name="url" value="${escapeHtml(event?.url ?? "")}"
               placeholder="https://...">
      </div>
    </form>`;
}

/**
 * `modalId` scopes the lookup: the create and edit modals both hold a form with
 * the same ids, and the closed one stays in the DOM. Reading by id alone found
 * the create form and posted a new event instead of updating.
 */
async function submitEventForm(modalId) {
    const form = modal(modalId).querySelector("#event-form");
    const id = form.dataset.eventId;
    const value = (name) => form.querySelector(`[name="${name}"]`).value.trim();

    const payload = { name: value("name"), starts_on: value("starts_on") };
    if (!payload.name) throw new Error("O nome é obrigatório.");
    if (!payload.starts_on) throw new Error("A data de início é obrigatória.");

    // The API rejects an explicit null, so empty optional fields are omitted.
    for (const field of ["location", "description", "url", "ends_on"]) {
        if (value(field)) payload[field] = value(field);
    }
    if (payload.ends_on && payload.ends_on < payload.starts_on) {
        throw new Error("O fim não pode ser anterior ao início.");
    }

    const res = await window.Auth.authFetch(
        id ? API.events.update(id) : API.events.create,
        {
            method: id ? "PUT" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        }
    );
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.message || "Não foi possível guardar.");
    }
}

function openForm({ id, event = null }) {
    bodyOf(id).innerHTML = eventForm(event);
    footOf(id).innerHTML = `
        <button class="button" data-modal-close>Cancelar</button>
        <button class="button is-dark" id="event-submit">
          ${event ? "Guardar alterações" : "Criar evento"}
        </button>`;
    open(id);

    document.getElementById("event-submit").onclick = (e) =>
        submitting(e.currentTarget, async () => {
            await submitEventForm(id);
            close(id);
            Notify.success(event ? "Evento actualizado." : "Evento criado.");
            await loadEvents();
        });
}

const getEvent = async (id) => {
    const res = await fetch(API.events.get(id));
    if (!res.ok) throw new Error("Evento não encontrado.");
    return res.json();
};

async function openDelete(id) {
    const event = await getEvent(id);

    bodyOf("deleteEventModal").innerHTML =
        `<p>Apagar <strong>${escapeHtml(event.name)}</strong>?</p>
         <p class="has-text-grey is-size-7 mt-2">
           Deixa de aparecer no percurso da página inicial.</p>`;
    footOf("deleteEventModal").innerHTML = `
        <button class="button" data-modal-close>Cancelar</button>
        <button class="button is-danger" id="event-delete">Apagar</button>`;
    open("deleteEventModal");

    document.getElementById("event-delete").onclick = (e) =>
        submitting(e.currentTarget, async () => {
            const res = await window.Auth.authFetch(API.events.delete(id), { method: "DELETE" });
            if (!res.ok) throw new Error("Não foi possível apagar.");
            close("deleteEventModal");
            Notify.success("Evento apagado.");
            await loadEvents();
        });
}

document.addEventListener("click", async (clicked) => {
    const trigger = clicked.target.closest("[data-event-action]");
    if (!trigger) return;

    const { eventAction: action, eventId: id } = trigger.dataset;
    if (action === "edit") openForm({ id: "editEventModal", event: await getEvent(id) });
    if (action === "delete") openDelete(id);
});

document.getElementById("new-event")
    ?.addEventListener("click", () => openForm({ id: "newEventModal" }));

loadEvents();
