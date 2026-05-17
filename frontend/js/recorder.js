export class Recorder {
  constructor() {
    this._mediaRecorder = null;
    this._chunks = [];
    this._stream = null;
  }

  /** Request mic access and start capturing audio. */
  async start() {
    this._stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this._chunks = [];

    // Prefer webm/opus; fall back to browser default
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : '';
    this._mediaRecorder = new MediaRecorder(
      this._stream,
      mimeType ? { mimeType } : {}
    );

    this._mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) this._chunks.push(e.data);
    };

    this._mediaRecorder.start(100); // collect chunks every 100 ms
  }

  /**
   * Stop recording and return the collected audio as a Blob.
   * @returns {Promise<Blob>}
   */
  stop() {
    return new Promise((resolve, reject) => {
      if (!this._mediaRecorder) {
        reject(new Error('Recorder not started'));
        return;
      }

      this._mediaRecorder.onstop = () => {
        const blob = new Blob(this._chunks, {
          type: this._mediaRecorder.mimeType || 'audio/webm',
        });
        this._stream.getTracks().forEach((t) => t.stop());
        this._stream = null;
        resolve(blob);
      };

      this._mediaRecorder.stop();
    });
  }

  get isRecording() {
    return this._mediaRecorder?.state === 'recording';
  }
}
