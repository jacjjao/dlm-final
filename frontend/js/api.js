const BASE_URL = 'http://100.92.125.6:8000';

async function request(path, options) {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`[${res.status}] ${path}: ${body || res.statusText}`);
  }
  return res.json();
}

/**
 * POST /transcribe — send audio blob, receive transcript text
 * @param {Blob} audioBlob
 * @returns {Promise<{text: string}>}
 */
export async function transcribeAudio(audioBlob) {
  const form = new FormData();
  form.append('audio', audioBlob, 'recording.webm');
  return request('/transcribe', { method: 'POST', body: form });
}

/**
 * POST /generate — send transcript, receive Python code
 * @param {string} transcript
 * @returns {Promise<{code: string}>}
 */
export async function generateCode(transcript) {
  return request('/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcript }),
  });
}

/**
 * POST /execute — run code in sandbox, receive stdout/stderr
 * @param {string} code
 * @returns {Promise<{stdout: string, stderr: string, exit_code: number}>}
 */
export async function executeCode(code) {
  return request('/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
}

/**
 * POST /debug — send broken code + error, receive fixed code
 * @param {string} code
 * @param {string} error
 * @param {string} transcript  original user intent
 * @returns {Promise<{code: string, explanation: string}>}
 */
export async function debugCode(code, error, transcript) {
  return request('/debug', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, error, transcript }),
  });
}
