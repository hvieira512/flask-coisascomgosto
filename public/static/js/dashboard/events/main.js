import { API, list, request } from "../../core/api.js";
import { Notify } from "../../core/notify.js";
import { confirmDialog, formDialog, modal } from "../../core/modal.js";
import { stepDialog } from "../../core/steps.js";
import { escapeHtml } from "../../core/html.js";
import { eventDates, stateChip } from "./dates.js";

async function loadEvents() {
    let events;
    try {
        events = await list(API.events.list, "events", { fallback: "Erro ao buscar feiras." });
    } catch (error) {
        Notify.error(error.message);
        return;
    }

    const rows = document.getElementById("event-rows");

    rows.innerHTML = events.length
        ? events.map((event) => `
            <tr data-event-id="${event.id}">
              <td class="dash-col-name">
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
             Ainda não há feiras.</td></tr>`;

    document.getElementById("event-count").textContent =
        `${events.length} ${events.length === 1 ? "feira" : "feiras"}`;
}

const EVENT_STEPS = ["Quando", "Detalhes"];

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
          </div>
        </div>

        <div class="row g-3">
          <div class="col">
            <label class="form-label fs-7" for="ef-starts">Início</label>
            <div class="input-group">
              <input class="form-control" id="ef-starts" name="starts_on" type="date" required
                     value="${escapeHtml(event?.starts_on ?? "")}">
            </div>
          </div>
          <div class="col">
            <label class="form-label fs-7" for="ef-ends">Fim</label>
            <div class="input-group">
              <input class="form-control" id="ef-ends" name="ends_on" type="date"
                     value="${escapeHtml(event?.ends_on ?? "")}">
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
          </div>
        </div>
      </div>
    </form>`;
}

function validateWhen(root) {
    const form = root.querySelector("#event-form");
    const value = (name) => form.querySelector(`[name="${name}"]`).value.trim();

    if (!value("name")) throw new Error("O nome é obrigatório.");
    if (!value("starts_on")) throw new Error("A data de início é obrigatória.");
    if (value("ends_on") && value("ends_on") < value("starts_on")) {
        throw new Error("O fim não pode ser anterior ao início.");
    }
}

async function submitEventForm(modalId) {
    const form = modal(modalId).querySelector("#event-form");
    const id = form.dataset.eventId;
    const value = (name) => form.querySelector(`[name="${name}"]`).value.trim();

    const payload = { name: value("name"), starts_on: value("starts_on") };
    if (!payload.name) throw new Error("O nome é obrigatório.");
    if (!payload.starts_on) throw new Error("A data de início é obrigatória.");

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

function openEdit({ id, event }) {
    formDialog({
        id,
        body: eventForm(event),
        submitLabel: "Guardar alterações",
        onSubmit: () => submitEventForm(id),
        success: "Feira actualizada.",
        after: loadEvents,
    });
}

function openCreate(id) {
    stepDialog({
        id,
        body: eventForm(),
        titles: EVENT_STEPS,
        validate: [validateWhen, validateWhen],
        finishLabel: "Criar feira",
        onFinish: () => submitEventForm(id),
        success: "Feira criada.",
        after: loadEvents,
    });
}

const getEvent = (id) =>
    request(API.events.get(id), { fallback: "Feira não encontrada." });

async function openDelete(id) {
    const event = await getEvent(id);

    confirmDialog({
        id: "deleteEventModal",
        body: `<p>Apagar <strong>${escapeHtml(event.name)}</strong>?</p>
               <p class="text-body-secondary fs-7 mt-2">
                 Deixa de aparecer no percurso da página inicial.</p>`,
        onConfirm: () => request(API.events.delete(id),
                                { method: "DELETE", fallback: "Não foi possível apagar." }),
        success: "Feira apagada.",
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

    const row = clicked.target.closest("#event-rows tr[data-event-id]");
    if (row) {
        openEdit({ id: "editEventModal", event: await getEvent(row.dataset.eventId) });
    }
});

document.getElementById("new-event")
    ?.addEventListener("click", () => openCreate("newEventModal"));

loadEvents();
