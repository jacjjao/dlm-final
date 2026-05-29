import { Recorder } from './recorder.js';
import { Editor } from './editor.js';
import { TTS } from './tts.js';
import * as api from './api.js';

// ─── Types ─────────────────────────────────────────────────────────────────

type StatusKey =
  | 'idle' | 'recording' | 'transcribing' | 'generating'
  | 'executing' | 'debugging' | 'done' | 'error';

type TerminalLineType = 'stdout' | 'stderr' | 'info';

type ToastType = 'info' | 'success' | 'error' | 'warning';

interface StatusConfig {
  dot: string;
  label: string;
  text: string;
}

// ─── DOM helpers ───────────────────────────────────────────────────────────

function getElement<T extends HTMLElement>(id: string): T {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Element #${id} not found in DOM`);
  return el as T;
}

// ─── DOM refs ──────────────────────────────────────────────────────────────

const recordBtn             = getElement<HTMLButtonElement>('record-btn');
const runBtn                = getElement<HTMLButtonElement>('run-btn');
const muteBtn               = getElement<HTMLButtonElement>('mute-btn');
const replayBtn             = getElement<HTMLButtonElement>('replay-btn');
const copyBtn               = getElement<HTMLButtonElement>('copy-btn');
const clearBtn              = getElement<HTMLButtonElement>('clear-btn');
const clearTerminalBtn      = getElement<HTMLButtonElement>('clear-terminal-btn');
const transcriptDisplay     = getElement<HTMLSpanElement>('transcript-display');
const transcriptPlaceholder = getElement<HTMLSpanElement>('transcript-placeholder');
const terminalOutput        = getElement<HTMLDivElement>('terminal-output');
const statusText            = getElement<HTMLSpanElement>('status-text');
const statusDot             = getElement<HTMLSpanElement>('status-dot');
const statusLabel           = getElement<HTMLSpanElement>('status-label');
const metaText              = getElement<HTMLSpanElement>('meta-text');
const debugOverlay          = getElement<HTMLDivElement>('debug-overlay');
const debugLabel            = getElement<HTMLSpanElement>('debug-label');

// ─── Modules ───────────────────────────────────────────────────────────────

const recorder   = new Recorder();
const codeEditor = getElement<HTMLTextAreaElement>('code-editor');
const editor     = new Editor(codeEditor);
const tts        = new TTS();

// ─── State ─────────────────────────────────────────────────────────────────

let currentTranscript = '';
let debugRetries = 0;
const MAX_RETRIES = 3;

// ─── Status ────────────────────────────────────────────────────────────────

const STATUS: Record<StatusKey, StatusConfig> = {
  idle:         { dot: 'idle',       label: 'Idle',            text: 'Ready' },
  recording:    { dot: 'recording',  label: 'Recording...',    text: 'Listening' },
  transcribing: { dot: 'processing', label: 'Transcribing...', text: 'Processing speech' },
  generating:   { dot: 'processing', label: 'Generating...',   text: 'Generating Python code' },
  executing:    { dot: 'processing', label: 'Executing...',    text: 'Running code' },
  debugging:    { dot: 'processing', label: 'Debugging...',    text: 'Fixing error automatically' },
  done:         { dot: 'done',       label: 'Done',            text: 'Complete' },
  error:        { dot: 'error',      label: 'Error',           text: 'An error occurred' },
};

function setStatus(state: StatusKey, overrideText?: string): void {
  const s = STATUS[state];
  statusDot.className     = `status-dot ${s.dot}`;
  statusLabel.textContent = s.label;
  statusText.textContent  = overrideText ?? s.text;
  statusText.classList.toggle('active', state !== 'idle' && state !== 'done');
}

// ─── Terminal ──────────────────────────────────────────────────────────────

function appendTerminal(text: string, type: TerminalLineType = 'stdout'): void {
  const placeholder = terminalOutput.querySelector('.terminal-placeholder');
  if (placeholder) placeholder.remove();

  String(text).split('\n').forEach((line) => {
    const el = document.createElement('div');
    el.className = `terminal-line ${type}`;
    el.textContent = line;
    terminalOutput.appendChild(el);
  });
  terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

function clearTerminal(): void {
  terminalOutput.innerHTML =
    '<div class="terminal-placeholder">Execution output will appear here...</div>';
}

// ─── Toast ─────────────────────────────────────────────────────────────────

function showToast(message: string, type: ToastType = 'info', duration = 4000): void {
  const container = getElement<HTMLDivElement>('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => toast.classList.add('show'));
  });

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ─── Recording ─────────────────────────────────────────────────────────────

async function handleRecord(): Promise<void> {
  if (recorder.isRecording) {
    void stopRecording();
  } else {
    await startRecording();
  }
}

async function startRecording(): Promise<void> {
  try {
    await recorder.start();
  } catch (err) {
    const error = err as DOMException;
    const msg =
      error.name === 'NotAllowedError'
        ? 'Microphone access denied. Please allow microphone access in your browser.'
        : `Microphone error: ${error.message}`;
    showToast(msg, 'error', 6000);
    setStatus('error', 'Microphone unavailable');
    return;
  }

  tts.stop();
  recordBtn.classList.add('recording');
  recordBtn.querySelector<HTMLSpanElement>('.record-text')!.textContent = 'Stop';
  recordBtn.setAttribute('aria-label', 'Stop recording (R)');
  setStatus('recording');
}

async function stopRecording(): Promise<void> {
  recordBtn.classList.remove('recording');
  recordBtn.querySelector<HTMLSpanElement>('.record-text')!.textContent = 'Record';
  recordBtn.setAttribute('aria-label', 'Start recording (R)');
  setStatus('transcribing');

  try {
    const audioBlob = await recorder.stop();
    await processAudio(audioBlob);
  } catch (err) {
    handleError(err as Error);
  }
}

// ─── Core pipeline ─────────────────────────────────────────────────────────

async function processAudio(audioBlob: Blob): Promise<void> {
  setStatus('transcribing');
  const { text } = await api.transcribeAudio(audioBlob);

  currentTranscript = text;
  transcriptDisplay.textContent = text;
  transcriptPlaceholder.style.display = 'none';

  setStatus('generating');
  const { code } = await api.generateCode(text);

  editor.setCode(code);
  copyBtn.disabled = false;
  clearBtn.disabled = false;
  runBtn.disabled = false;

  tts.speak('Code generated. Running now.');

  await runCode(code);
}

async function runCode(code: string): Promise<void> {
  setStatus('executing');
  clearTerminal();
  debugRetries = 0;
  metaText.textContent = '';

  const result = await api.executeCode(code);

  if (result.exit_code === 0) {
    if (result.stdout) appendTerminal(result.stdout, 'stdout');
    setStatus('done');
    replayBtn.disabled = false;

    const preview = result.stdout.trim();
    tts.speak(
      preview
        ? `Done. ${preview.length > 180 ? preview.slice(0, 180) + '...' : preview}`
        : 'Code executed successfully with no output.',
    );
  } else {
    if (result.stderr) appendTerminal(result.stderr, 'stderr');
    await attemptDebug(code, result.stderr);
  }
}

async function attemptDebug(code: string, error: string): Promise<void> {
  if (debugRetries >= MAX_RETRIES) {
    hideDebugOverlay();
    setStatus('error', `Could not fix error after ${MAX_RETRIES} attempts`);
    tts.speak("I couldn't fix the error automatically. Please check the terminal for details.");
    replayBtn.disabled = false;
    return;
  }

  debugRetries++;
  setStatus('debugging');
  showDebugOverlay(`Auto-fixing… attempt ${debugRetries} of ${MAX_RETRIES}`);

  const { code: fixedCode, explanation } = await api.debugCode(code, error, currentTranscript);

  editor.setCode(fixedCode);
  clearTerminal();
  appendTerminal(`[Auto-fix ${debugRetries}/${MAX_RETRIES}] ${explanation}`, 'info');

  const result = await api.executeCode(fixedCode);

  if (result.exit_code === 0) {
    hideDebugOverlay();
    if (result.stdout) appendTerminal(result.stdout, 'stdout');
    setStatus('done');
    replayBtn.disabled = false;

    const preview = result.stdout.trim().slice(0, 120);
    tts.speak(
      `Code had an error, but I fixed it. ${preview ? "Here's the result: " + preview : 'Execution successful.'}`,
    );
  } else {
    if (result.stderr) appendTerminal(result.stderr, 'stderr');
    await attemptDebug(fixedCode, result.stderr);
  }
}

// ─── Debug overlay helpers ─────────────────────────────────────────────────

function showDebugOverlay(label: string): void {
  debugLabel.textContent = label;
  metaText.textContent = `Attempt ${debugRetries}/${MAX_RETRIES}`;
  debugOverlay.hidden = false;
  debugOverlay.removeAttribute('aria-hidden');
}

function hideDebugOverlay(): void {
  debugOverlay.hidden = true;
  debugOverlay.setAttribute('aria-hidden', 'true');
  metaText.textContent = '';
}

// ─── Error handler ─────────────────────────────────────────────────────────

function handleError(err: Error): void {
  console.error('[VocalCode]', err);
  hideDebugOverlay();
  setStatus('error', err.message);

  const isNetworkError =
    err.message.includes('fetch') ||
    err.message.includes('Failed to fetch') ||
    err.message.includes('NetworkError');

  showToast(
    isNetworkError
      ? 'Cannot reach backend. Start the FastAPI server on port 8000.'
      : `Error: ${err.message}`,
    'error',
    6000,
  );
}

// ─── Event listeners ───────────────────────────────────────────────────────

recordBtn.addEventListener('click', () => void handleRecord());

runBtn.addEventListener('click', () => {
  const code = editor.getCode();
  if (!code) return;
  runCode(code).catch(handleError);
});

muteBtn.addEventListener('click', () => {
  const muted = tts.toggleMute();
  muteBtn.classList.toggle('muted', muted);
  muteBtn.setAttribute('aria-label', muted ? 'Unmute text-to-speech' : 'Mute text-to-speech');
  muteBtn.title = muted ? 'Unmute TTS (M)' : 'Mute TTS (M)';
  muteBtn.querySelector('path')!.setAttribute(
    'd',
    muted
      ? 'M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z'
      : 'M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z',
  );
  showToast(muted ? 'TTS muted' : 'TTS unmuted');
});

replayBtn.addEventListener('click', () => tts.replay());

copyBtn.addEventListener('click', () => {
  const code = editor.getCode();
  if (!code) return;
  navigator.clipboard
    .writeText(code)
    .then(() => showToast('Code copied to clipboard!', 'success'))
    .catch(() => showToast('Clipboard access denied', 'error'));
});

clearBtn.addEventListener('click', () => {
  editor.clear();
  copyBtn.disabled = true;
  clearBtn.disabled = true;
  runBtn.disabled = true;
  replayBtn.disabled = true;
  setStatus('idle');
  tts.stop();
});

clearTerminalBtn.addEventListener('click', clearTerminal);

codeEditor.addEventListener('input', () => {
  const hasCode = !editor.isEmpty();
  copyBtn.disabled  = !hasCode;
  clearBtn.disabled = !hasCode;
  runBtn.disabled   = !hasCode;
});

codeEditor.addEventListener('keydown', (e: KeyboardEvent) => {
  if (e.key !== 'Tab') return;
  e.preventDefault();
  const start = codeEditor.selectionStart;
  const end   = codeEditor.selectionEnd;
  codeEditor.value = codeEditor.value.slice(0, start) + '    ' + codeEditor.value.slice(end);
  codeEditor.selectionStart = codeEditor.selectionEnd = start + 4;
});

// ─── Keyboard shortcuts ────────────────────────────────────────────────────

document.addEventListener('keydown', (e: KeyboardEvent) => {
  const target = e.target as HTMLElement;
  if (['INPUT', 'TEXTAREA'].includes(target.tagName)) return;

  switch (e.key.toLowerCase()) {
    case 'r':
      e.preventDefault();
      void handleRecord();
      break;
    case ' ':
      if (!runBtn.disabled) {
        e.preventDefault();
        runBtn.click();
      }
      break;
    case 'm':
      e.preventDefault();
      muteBtn.click();
      break;
  }
});

// ─── Init ──────────────────────────────────────────────────────────────────

setStatus('idle');
