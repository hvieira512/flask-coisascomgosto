import { API, request } from "../../core/api.js";
import { Notify } from "../../core/notify.js";
import { confirmDialog, formDialog, modal } from "../../core/modal.js";
import { stepDialog } from "../../core/steps.js";
import { escapeHtml, fieldIcon } from "../../core/html.js";
import { eventDates, stateChip } from "./dates.js";

async function loadEvents() {
    let events;
    try {
        ({ events } = await request(`${API.events.list}?limit=100`,
                                   { fallback: "Erro ao buscar eventos." }));
    } catch (error) {
        Notify.error(error.message);
        return;
    }

    const rows = document.getElementById("event-rows");

    rows.innerHTML = events.length
        ? events.map((event) => `
            <tr data-event-id="${event.id}">
              <td>
                <p class="fw-medium mb-0">
                  ${escapeHtml(event.name)}
                  ${stateChip(event, { extraClass: "ms-2" })}
                </p>
                ${event.description
                    ? `<p class="fs-7 text-body-secondary mb-0">${escapeHtml(event.description)}</p>`
                    : ""}
              </td>
              <td class="fs-7 text-body-secondary">${escapeHtml(event.location ?? "—")}</td>
              <td class="data text-body-secondary">${escapeHtml(eventDates(event))}</td>
              <td class="dash-col-actions">
                <span class="dash-row-actions d-flex gap-1">
                  <button class="btn btn-sm btn-ghost" data-event-action="edit"
                          data-event-id="${event.id}" title="Editar"
                          aria-label="Editar ${escapeHtml(event.name)}">
                    <span class="icon"><i class="fa-solid fa-pencil"></i></span>
                  </button>
                  <button class="btn btn-sm btn-ghost text-danger"
                          data-event-action="delete" data-event-id="${event.id}" title="Apagar"
                          aria-label="Apagar ${escapeHtml(event.name)}">
                    <span class="icon"><i class="fa-solid fa-trash"></i></span>
                  </button>
                </span>
              </td>
            </tr>`).join("")
        : `<tr><td colspan="4" class="text-center text-body-secondary py-5">
             Ainda não há eventos.</td></tr>`;

    document.getElementById("event-count").textContent =
        `${events.length} ${events.length === 1 ? "evento" : "eventos"}`;
}

const EVENT_STEPS = ["Quando", "Detalhes"];

/**
 * Two `data-step` groups: the name and the dates the API insists on, then the
 * rest. core/steps.js shows one at a time when creating; editing leaves both
 * visible.
 */
function eventForm(event = null) {
    return `
    <form id="event-form" data-event-id="${event?.id ?? ""}">
      <div data-step="when">
        <div class="mb-3">
          <label class="form-label fs-7" for="ef-name">Nome</label>
          <div class="input-group">
            <input class="form-control" id="ef-name" name="name" required
                   value="${escapeHtml(event?.name ?? "")}"
                   placeholder="Feira de Artesanato da Romaria d'Agonia">
            ${fieldIcon("fa-solid fa-tag")}
          </div>
        </div>

        <div class="row g-3">
          <div class="col">
            <label class="form-label fs-7" for="ef-starts">Início</label>
            <div class="input-group">
              <input class="form-control" id="ef-starts" name="starts_on" type="date" required
                     value="${escapeHtml(event?.starts_on ?? "")}">
              ${fieldIcon("fa-solid fa-calendar-day")}
            </div>
          </div>
          <div class="col">
            <label class="form-label fs-7" for="ef-ends">Fim</label>
            <div class="input-group">
              <input class="form-control" id="ef-ends" name="ends_on" type="date"
                     value="${escapeHtml(event?.ends_on ?? "")}">
              ${fieldIcon("fa-solid fa-calendar-check")}
            </div>
            <p class="help mb-0">Deixe vazio se for de um só dia.</p>
          </div>
        </div>
      </div>

      <div data-step="details">
        <div class="mb-3">
          <label class="form-label fs-7" for="ef-location">Local</label>
          <div class="input-group">
            <input class="form-control" id="ef-location" name="location"
                   value="${escapeHtml(event?.location ?? "")}"
                   placeholder="Jardim Público, Viana do Castelo">
            ${fieldIcon("fa-solid fa-location-dot")}
          </div>
        </div>

        <div class="mb-3">
          <label class="form-label fs-7" for="ef-description">Descrição</label>
          <textarea class="form-control" id="ef-description" name="description" rows="2"
                    >${escapeHtml(event?.description ?? "")}</textarea>
        </div>

        <div>
          <label class="form-label fs-7" for="ef-url">Ligação</label>
          <div class="input-group">
            <input class="form-control" id="ef-url" name="url" value="${escapeHtml(event?.url ?? "")}"
                   placeholder="https://...">
            ${fieldIcon("fa-solid fa-link")}
          </div>
        </div>
      </div>
    </form>`;
}

/** The dates step's own check, run before it will let go. */
function validateWhen(root) {
    const form = root.querySelector("#event-form");
    const value = (name) => form.querySelector(`[name="${name}"]`).value.trim();

    if (!value("name")) throw new Error("O nome é obrigatório.");
    if (!value("starts_on")) throw new Error("A data de início é obrigatória.");
    if (value("ends_on") && value("ends_on") < value("starts_on")) {
        throw new Error("O fim não pode ser anterior ao início.");
    }
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

    await request(id ? API.events.update(id) : API.events.create, {
        method: id ? "PUT" : "POST",
        body: payload,
        fallback: "Não foi possível guardar.",
    });
}

/** Editing is changing one thing, so it stays a single screen. */
function openEdit({ id, event }) {
    formDialog({
        id,
        body: eventForm(event),
        submitLabel: "Guardar alterações",
        onSubmit: () => submitEventForm(id),
        success: "Evento actualizado.",
        after: loadEvents,
    });
}

function openCreate(id) {
    stepDialog({
        id,
        body: eventForm(),
        titles: EVENT_STEPS,
        validate: [validateWhen, validateWhen],
        finishLabel: "Criar evento",
        onFinish: () => submitEventForm(id),
        success: "Evento criado.",
        after: loadEvents,
    });
}

const getEvent = (id) =>
    request(API.events.get(id), { fallback: "Evento não encontrado." });

async function openDelete(id) {
    const event = await getEvent(id);

    confirmDialog({
        id: "deleteEventModal",
        body: `<p>Apagar <strong>${escapeHtml(event.name)}</strong>?</p>
               <p class="text-body-secondary fs-7 mt-2">
                 Deixa de aparecer no percurso da página inicial.</p>`,
        onConfirm: () => request(API.events.delete(id),
                                { method: "DELETE", fallback: "Não foi possível apagar." }),
        success: "Evento apagado.",
        after: loadEvents,
    });
}

document.addEventListener("click", async (clicked) => {
    const trigger = clicked.target.closest("[data-event-action]");
    if (trigger) {
        const { eventAction: action, eventId: id } = trigger.dataset;
        if (action === "edit") openEdit({ id: "editEventModal", event: await getEvent(id) });
        if (action === "delete") openDelete(id);
        return;
    }

    // The whole row opens the event, matching the catalogue.
    const row = clicked.target.closest("#event-rows tr[data-event-id]");
    if (row) {
        openEdit({ id: "editEventModal", event: await getEvent(row.dataset.eventId) });
    }
});

document.getElementById("new-event")
    ?.addEventListener("click", () => openCreate("newEventModal"));

loadEvents();
