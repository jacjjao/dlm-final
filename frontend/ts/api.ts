const BASE_URL = 'http://100.92.125.6:8000';

export interface TranscribeResponse {
  text: string;
}

export interface GenerateResponse {
  type: 'code' | 'chat';
  code: string;
  reply: string;
}

export interface ExecuteResponse {
  stdout: string;
  stderr: string;
  exit_code: number;
}

export interface DebugResponse {
  code: string;
  explanation: string;
}

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`[${res.status}] ${path}: ${body || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function transcribeAudio(audioBlob: Blob): Promise<TranscribeResponse> {
  const form = new FormData();
  form.append('audio', audioBlob, 'recording.webm');
  return request<TranscribeResponse>('/transcribe', { method: 'POST', body: form });
}

export async function generateCode(transcript: string): Promise<GenerateResponse> {
  return request<GenerateResponse>('/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcript }),
  });
}

export async function executeCode(code: string): Promise<ExecuteResponse> {
  return request<ExecuteResponse>('/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
}

export async function debugCode(
  code: string,
  error: string,
  transcript: string,
): Promise<DebugResponse> {
  return request<DebugResponse>('/debug', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, error, transcript }),
  });
}
