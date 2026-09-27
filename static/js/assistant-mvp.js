const form = document.querySelector('#assistant-form');
const input = document.querySelector('#assistant-message');
const language = document.querySelector('#language');
const conversation = document.querySelector('#conversation');
const status = document.querySelector('#assistant-status');
const voiceButton = document.querySelector('#voice-button');
const languageVoices = { Hindi: 'hi-IN', English: 'en-IN', Marathi: 'mr-IN', Tamil: 'ta-IN', Telugu: 'te-IN' };

document.querySelectorAll('.quick-actions button').forEach((button) => button.addEventListener('click', () => { input.value = button.dataset.question; form.requestSubmit(); }));

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) return;
    addMessage('You', message, 'user-message');
    input.value = '';
    status.textContent = 'Preparing simple advice...';
    try {
        const response = await fetch('/api/assistant', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message, language: language.value }) });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Please try again.');
        addMessage('Uyirnilam', data.answer, 'assistant-message', true);
        status.textContent = `Context used: ${data.context_used.join(' · ')}`;
    } catch (error) { status.textContent = error.message; }
});

function addMessage(label, text, className, canSpeak = false) {
    const message = document.createElement('div');
    message.className = `message ${className}`;
    message.innerHTML = `<span class="message-label">${label}</span><p>${text}</p>${canSpeak ? `<button class="listen-button" type="button">🔊 सुनें / Listen</button>` : ''}`;
    conversation.appendChild(message);
    if (canSpeak) message.querySelector('.listen-button').addEventListener('click', () => speakResponse(text, language.value));
    message.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function speakResponse(text, selectedLanguage) {
    if (!('speechSynthesis' in window)) return;
    speechSynthesis.cancel();
    const languageCode = languageVoices[selectedLanguage] || 'hi-IN';
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
    const languageVoices = voices.filter((voice) => voice.lang.toLowerCase().startsWith(languageCode.slice(0, 2).toLowerCase()));
    const femaleNames = /(female|lekha|veena|heera|samantha|karen|susan|zira|siri)/i;
    const maleNames = /(male|ravi|hemant|rishi|alex)/i;
    return languageVoices.find((voice) => femaleNames.test(`${voice.name} ${voice.voiceURI}`))
        || languageVoices.find((voice) => !maleNames.test(`${voice.name} ${voice.voiceURI}`))
        || null;
}

if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new Recognition();
    recognition.lang = languageVoices[language.value];
    recognition.onstart = () => { voiceButton.querySelector('span').textContent = 'Listening...'; };
    recognition.onend = () => { voiceButton.querySelector('span').textContent = 'Tap to speak'; };
    recognition.onresult = (event) => { input.value = event.results[0][0].transcript; form.requestSubmit(); };
    voiceButton.addEventListener('click', () => { recognition.lang = languageVoices[language.value]; recognition.start(); });
} else {
    voiceButton.addEventListener('click', () => { status.textContent = 'Voice input is not supported in this browser. You can type your question.'; });
}
