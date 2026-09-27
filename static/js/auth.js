const googleTriggers = document.querySelectorAll("[data-google-trigger]");

googleTriggers.forEach((trigger) => trigger.addEventListener("click", () => {
    const emailField = document.querySelector("#phone");
    const nameField = document.querySelector("#name");
    const locationField = document.querySelector("#location");
    const status = document.querySelector("[data-google-status]");

    if (emailField) emailField.value = "demo@uyirnilam.local";
    if (nameField && !nameField.value) nameField.value = "Ravi Kumar";
    if (locationField && !locationField.value) locationField.value = "Pune, Maharashtra";
    if (status) status.textContent = "Google account selected: demo@uyirnilam.local";
    emailField?.focus();
}));