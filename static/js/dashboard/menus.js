const toggle = document.querySelector("#sidebarToggle");
const overlay = document.querySelector("#overlay");
const mobileSidebar = document.querySelector("#mobileSidebar");
const closeSidebar = document.querySelector("#closeSidebar");

const toggleSidebar = (show) => {
    mobileSidebar.classList.toggle("d-none", !show);
    mobileSidebar.classList.toggle("d-block", show);

    overlay.classList.toggle("d-none", !show);
    overlay.classList.toggle("d-block", show);
};

toggle.addEventListener("click", () => toggleSidebar(true));
closeSidebar.addEventListener("click", () => toggleSidebar(false));
overlay.addEventListener("click", () => toggleSidebar(false));
