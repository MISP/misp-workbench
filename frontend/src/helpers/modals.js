export const modals = {
    closeAll() {
        const modals = document.querySelectorAll(".modal");
        modals.forEach((modal) => {
            modal.classList.remove("show");
        });
        const backdrops = document.querySelectorAll(".modal-backdrop");
        backdrops.forEach((backdrop) => {
            backdrop.hidden = true;
        });
        document.querySelector("body").classList.remove("modal-open");
        document.querySelector("body").style.overflow = "auto";
    }
};
