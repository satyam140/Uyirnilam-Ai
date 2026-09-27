const form = document.querySelector("#crop-analysis-form");
const imageInput = document.querySelector("#crop-image");
const preview = document.querySelector("#image-preview");
const uploadTitle = document.querySelector("#upload-title");
const uploadHelp = document.querySelector("#upload-help");
const status = document.querySelector("#form-status");
const result = document.querySelector("#diagnosis-result");

imageInput.addEventListener("change", () => {
    const file = imageInput.files[0];
    if (!file) return;
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
    uploadTitle.textContent = file.name;
    uploadHelp.textContent = "Photo selected. Ready to check.";
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = form.querySelector("button");
    submit.disabled = true;
    status.textContent = "Analyzing your crop...";
    result.hidden = true;
    try {
        const response = await fetch("/api/analyze-crop", { method: "POST", body: new FormData(form) });
        const diagnosis = await response.json();
        if (!response.ok) throw new Error(diagnosis.error || "We could not analyze that image.");
        result.innerHTML = renderDiagnosis(diagnosis);
        result.hidden = false;
        result.querySelector("[data-save-diagnosis]").addEventListener("click", () => saveDiagnosis(diagnosis));
        status.textContent = "Your crop check is ready.";
        result.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
        status.textContent = error.message;
    } finally {
        submit.disabled = false;
    }
});

function renderDiagnosis(diagnosis) {
    return `<div class="result-heading"><div><p class="eyebrow">Crop health report</p><h2>Here's what we <em>found.</em></h2></div><span class="severity-badge">${diagnosis.severity} severity</span></div>
        <div class="diagnosis-summary"><div><span class="label">Crop</span><strong>${diagnosis.crop}</strong></div><div><span class="label">Likely condition</span><strong>${diagnosis.condition}</strong></div><div><span class="label">Confidence</span><strong>${diagnosis.confidence}%</strong></div></div>
        <div class="diagnosis-columns"><div><p class="eyebrow">What we noticed</p><ul>${diagnosis.symptoms.map((item) => `<li>${item}</li>`).join("")}</ul><p class="result-explanation">${diagnosis.explanation}</p></div><div><p class="eyebrow">What you can do now</p><ol>${diagnosis.immediate_actions.map((item) => `<li>${item}</li>`).join("")}</ol></div></div>
        <div class="treatment-strip"><div><span class="label">Organic option</span><strong>${diagnosis.organic_treatment.name}</strong><p>${diagnosis.organic_treatment.application}</p></div><div><span class="label">Prevention</span><strong>${diagnosis.prevention[0]}</strong><p>${diagnosis.prevention.slice(1).join(" ")}</p></div></div>${diagnosis.demo_note ? `<p class="demo-note">${diagnosis.demo_note}</p>` : ""}<button class="button button-primary result-save" data-save-diagnosis>Save diagnosis</button>`;
}

    async function saveDiagnosis(diagnosis) {
        const saveButton = result.querySelector("[data-save-diagnosis]");
        saveButton.disabled = true;
        saveButton.textContent = "Saving...";
        const response = await fetch("/api/diagnoses/save", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(diagnosis) });
        const data = await response.json();
        saveButton.textContent = response.ok ? "Diagnosis saved" : (data.error || "Could not save");
    }
