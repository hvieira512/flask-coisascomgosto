import { escapeHtml } from "../core/html.js";

/* A chip you click to include, several at a time: the collections a colour set
   appears in, the materials a piece is made of. Both are unordered "which of
   these" questions, and both used to be written out where they were needed.

   The chips themselves are the state. Keeping a Set in step with them was one
   more thing that could disagree with what the owner can see, and the answer is
   read back once, at submit. */

export const pickChip = (id, label, chosen) => `
  <button type="button" data-pick="${id}" aria-pressed="${chosen}"
          class="badge rounded-pill chip is-quiet pick-chip${chosen ? " is-active" : ""}">
    ${escapeHtml(label)}
  </button>`;

export function wirePicks(container) {
    container.addEventListener("click", (event) => {
        const chip = event.target.closest(".pick-chip");
        if (!chip) return;

        const on = chip.getAttribute("aria-pressed") !== "true";
        chip.setAttribute("aria-pressed", String(on));
        chip.classList.toggle("is-active", on);
    });
}

export const picked = (container) =>
    [...container.querySelectorAll('.pick-chip[aria-pressed="true"]')]
        .map((chip) => Number(chip.dataset.pick));
