export class Recorder {
  private _mediaRecorder: MediaRecorder | null = null;
  private _chunks: Blob[] = [];
  private _stream: MediaStream | null = null;

  async start(): Promise<void> {
    this._stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this._chunks = [];

    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : '';
    this._mediaRecorder = new MediaRecorder(
      this._stream,
      mimeType ? { mimeType } : {},
    );

    this._mediaRecorder.ondataavailable = (e: BlobEvent) => {
      if (e.data.size > 0) this._chunks.push(e.data);
    };

    this._mediaRecorder.start(100);
  }

  stop(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this._mediaRecorder) {
        reject(new Error('Recorder not started'));
        return;
      }

      this._mediaRecorder.onstop = () => {
        const blob = new Blob(this._chunks, {
          type: this._mediaRecorder!.mimeType || 'audio/webm',
        });
        this._stream!.getTracks().forEach((t) => t.stop());
        this._stream = null;
        resolve(blob);
      };

      this._mediaRecorder.stop();
    });
  }

  get isRecording(): boolean {
    return this._mediaRecorder?.state === 'recording';
  }
}
