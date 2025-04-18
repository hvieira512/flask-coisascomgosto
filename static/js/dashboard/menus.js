const toggle = document.querySelector("#sidebarToggle");
const overlay = document.querySelector("#overlay");
const mobileSidebar = document.querySelector("#mobileSidebar");
const closeSidebar = document.querySelector("#closeSidebar");

const showSidebar = () => {
    mobileSidebar.classList.remove("d-none");
    mobileSidebar.classList.add("d-block");

    overlay.classList.remove("d-none");
    overlay.classList.add("d-block");
}

const hideSidebar = () => {
    mobileSidebar.classList.remove("d-block");
    mobileSidebar.classList.add("d-none");

    overlay.classList.remove("d-block");
    overlay.classList.add("d-none");
}

toggle.addEventListener("click", showSidebar);
closeSidebar.addEventListener("click", hideSidebar);
overlay.addEventListener("click", hideSidebar);
