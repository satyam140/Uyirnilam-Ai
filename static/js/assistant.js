const assistantForm = document.querySelector("#assistant-form");
const assistantInput = document.querySelector("#assistant-message");
const conversation = document.querySelector("#conversation");
const assistantStatus = document.querySelector("#assistant-status");
const assistantLanguage = document.body.dataset.assistantLanguage || "Hindi";

document.querySelectorAll(".quick-actions button").forEach((button) => button.addEventListener("click", () => {
    assistantInput.value = button.dataset.question;
    assistantForm.requestSubmit();
}));

assistantForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = assistantInput.value.trim();
    if (!message) return;
    addMessage("You", message, "user-message");
    assistantInput.value = "";
    assistantStatus.textContent = "Preparing farm advice...";
    try {
        const response = await fetch("/api/assistant", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message, language: assistantLanguage }) });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "The assistant could not answer right now.");
        addMessage("Uyirnilam Assistant", data.answer, "assistant-message", true);
        assistantStatus.textContent = `Context used: ${data.context_used.join(" · ")}`;
    } catch (error) { assistantStatus.textContent = error.message; }
});

function addMessage(label, text, className, canSpeak = false) {
    const message = document.createElement("div");
    message.className = `message ${className}`;
    message.innerHTML = `<span class="message-label">${label}</span><p>${text}</p>${canSpeak ? '<button class="listen-button" type="button">🔊 सुनें / Listen</button>' : ""}`;
    conversation.appendChild(message);
    if (canSpeak) message.querySelector(".listen-button").addEventListener("click", () => speakResponse(text));
    message.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function speakResponse(text) {
    if (!("speechSynthesis" in window)) return;
    speechSynthesis.cancel();
    const languageCode = assistantLanguage.toLowerCase() === "hindi" ? "hi-IN" : "en-IN";
    const chunks = text.match(/[^.!?।]+[.!?।]+|[^.!?।]+$/g) || [text];
    let index = 0;
    const speakNext = () => {
        if (index >= chunks.length) return;
        const utterance = new SpeechSynthesisUtterance(chunks[index].trim());
        utterance.lang = languageCode;
        utterance.rate = 0.9;
        const voices = speechSynthesis.getVoices();
        utterance.voice = findFemaleVoice(voices, languageCode);
        index += 1;
        utterance.onend = speakNext;
        speechSynthesis.speak(utterance);
    };
    speakNext();
}

function findFemaleVoice(voices, languageCode) {
    const languageVoices = voices.filter((voice) => voice.lang.toLowerCase().startsWith(languageCode.slice(0, 2)));
    const femaleNames = /(female|lekha|veena|heera|samantha|karen|susan|zira|siri)/i;
    const maleNames = /(male|ravi|hemant|rishi|alex)/i;
    return languageVoices.find((voice) => femaleNames.test(`${voice.name} ${voice.voiceURI}`))
        || languageVoices.find((voice) => !maleNames.test(`${voice.name} ${voice.voiceURI}`))
        || null;
}
