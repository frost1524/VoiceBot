'use strict';

// ── DOM refs ──
const transcriptEl = document.getElementById('transcript');
const statusDot    = document.getElementById('statusDot');
const statusText   = document.getElementById('statusText');
const micBtn       = document.getElementById('micBtn');
const startBtn     = document.getElementById('startBtn');
const endBtn       = document.getElementById('endBtn');
const agentCard    = document.getElementById('agentCard');

// ── State ──
let ws           = null;
let audioCtx     = null;
let micStream    = null;
let processor    = null;
let sourceNode   = null;
let isRecording  = false;
let nextPlayTime = 0;
let currentBotEl = null;

// ── Status helpers ──
function setStatus(state, text) {
    statusDot.className = 'status-dot ' + (state || '');
    statusText.textContent = text;
}

// ── Transcript helpers ──
function clearPlaceholder() {
    const ph = transcriptEl.querySelector('.transcript-placeholder');
    if (ph) ph.remove();
}

function appendMessage(role, text) {
    clearPlaceholder();
    const el = document.createElement('div');
    el.className = 'transcript-msg ' + role;
    el.innerHTML =
        `<div class="transcript-msg-label">${role === 'bot' ? '🤖 Priya' : '👤 You'}</div>` +
        `<div class="transcript-msg-bubble"></div>`;
    el.querySelector('.transcript-msg-bubble').textContent = text;
    transcriptEl.appendChild(el);
    transcriptEl.scrollTop = transcriptEl.scrollHeight;
    return el;
}

function appendToBubble(el, text) {
    el.querySelector('.transcript-msg-bubble').textContent += text;
    transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

// ── PCM16 helpers ──
function floatTo16BitPCM(float32) {
    const buf  = new ArrayBuffer(float32.length * 2);
    const view = new DataView(buf);
    for (let i = 0; i < float32.length; i++) {
        const s = Math.max(-1, Math.min(1, float32[i]));
        view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    return buf;
}

function bufferToBase64(buf) {
    const bytes = new Uint8Array(buf);
    let bin = '';
    for (let i = 0; i < bytes.byteLength; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin);
}

function base64ToFloat32(b64) {
    const bin   = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const pcm16  = new Int16Array(bytes.buffer);
    const f32    = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) f32[i] = pcm16[i] / 32768;
    return f32;
}

// ── Audio playback (time-scheduled for gapless streaming) ──
function playChunk(b64Audio) {
    if (!audioCtx) return;
    const f32    = base64ToFloat32(b64Audio);
    const buffer = audioCtx.createBuffer(1, f32.length, 24000);
    buffer.copyToChannel(f32, 0);
    const src = audioCtx.createBufferSource();
    src.buffer = buffer;
    src.connect(audioCtx.destination);
    const start = Math.max(audioCtx.currentTime, nextPlayTime);
    src.start(start);
    nextPlayTime = start + buffer.duration;
}

// ── Server event handler ──
function handleEvent(event) {
    switch (event.type) {

        case 'session.updated':
            setStatus('connected', 'Connected — hold the button to speak');
            micBtn.disabled = false;
            break;

        case 'response.audio.delta':
            setStatus('speaking', 'Priya is speaking…');
            playChunk(event.delta);
            break;

        case 'response.audio.done':
            nextPlayTime = 0;
            setStatus('connected', 'Connected — hold the button to speak');
            currentBotEl = null;
            break;

        case 'response.audio_transcript.delta':
            if (!currentBotEl) currentBotEl = appendMessage('bot', '');
            appendToBubble(currentBotEl, event.delta);
            break;

        case 'response.audio_transcript.done':
            currentBotEl = null;
            break;

        case 'conversation.item.input_audio_transcription.completed':
            appendMessage('user', event.transcript.trim());
            break;

        case 'agent_connect':
            showAgentCard(event.data);
            break;

        case 'error':
            console.error('Realtime error:', event);
            setStatus('', 'Error — check console');
            break;
    }
}

// ── Agent connect UI ──
function showAgentCard(data) {
    document.getElementById('queuePosition').textContent = `#${data.queue_position}`;
    document.getElementById('waitTime').textContent      = `~${data.wait_time_minutes} min`;
    document.getElementById('caseNumber').textContent    = `#${data.case_number}`;
    agentCard.style.display = 'block';
    micBtn.disabled         = true;
    setStatus('', 'Connecting to human agent…');
}

// ── Recording ──
async function startRecording() {
    if (!ws || ws.readyState !== WebSocket.OPEN || isRecording) return;
    try {
        await audioCtx.resume();
        micStream  = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 24000, channelCount: 1 } });
        sourceNode = audioCtx.createMediaStreamSource(micStream);
        processor  = audioCtx.createScriptProcessor(4096, 1, 1);

        processor.onaudioprocess = (e) => {
            if (!isRecording || !ws || ws.readyState !== WebSocket.OPEN) return;
            const pcm16 = floatTo16BitPCM(e.inputBuffer.getChannelData(0));
            ws.send(JSON.stringify({ type: 'input_audio_buffer.append', audio: bufferToBase64(pcm16) }));
        };

        sourceNode.connect(processor);
        processor.connect(audioCtx.destination);
        isRecording = true;
        micBtn.classList.add('recording');
        setStatus('listening', 'Listening…');
    } catch (err) {
        alert('Microphone access denied. Please allow mic access and try again.');
    }
}

function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    micBtn.classList.remove('recording');

    if (processor)  { processor.disconnect();  processor  = null; }
    if (sourceNode) { sourceNode.disconnect();  sourceNode = null; }
    if (micStream)  { micStream.getTracks().forEach(t => t.stop()); micStream = null; }

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'input_audio_buffer.commit' }));
        ws.send(JSON.stringify({ type: 'response.create' }));
        setStatus('connected', 'Processing…');
    }
}

// ── Session ──
function startSession() {
    audioCtx     = new AudioContext({ sampleRate: 24000 });
    nextPlayTime = 0;
    currentBotEl = null;

    ws = new WebSocket(`ws://${location.host}/ws`);

    ws.onopen  = () => setStatus('connected', 'Connecting to Priya…');
    ws.onclose = () => {
        setStatus('', 'Disconnected');
        micBtn.disabled  = true;
        startBtn.disabled = false;
        endBtn.disabled   = true;
    };
    ws.onerror = () => setStatus('', 'Connection error');
    ws.onmessage = (e) => {
        try { handleEvent(JSON.parse(e.data)); } catch (_) {}
    };

    startBtn.disabled = true;
    endBtn.disabled   = false;
}

function endSession() {
    if (ws) { ws.close(); ws = null; }
    if (audioCtx) { audioCtx.close(); audioCtx = null; }
    stopRecording();
}

// ── Button bindings ──
micBtn.addEventListener('mousedown',  startRecording);
micBtn.addEventListener('mouseup',    stopRecording);
micBtn.addEventListener('mouseleave', stopRecording);
micBtn.addEventListener('touchstart', (e) => { e.preventDefault(); startRecording(); }, { passive: false });
micBtn.addEventListener('touchend',   (e) => { e.preventDefault(); stopRecording();  }, { passive: false });

startBtn.addEventListener('click', startSession);
endBtn.addEventListener('click',   endSession);
