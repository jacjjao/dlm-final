export class TTS {
  private readonly _synth: SpeechSynthesis;
  private _muted: boolean = false;
  private _lastText: string = '';

  constructor() {
    this._synth = window.speechSynthesis;
  }

  speak(text: string): void {
    this._lastText = text;
    if (this._muted || !text) return;

    this._synth.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    this._synth.speak(utterance);
  }

  stop(): void {
    this._synth.cancel();
  }

  replay(): void {
    if (this._lastText) this.speak(this._lastText);
  }

  toggleMute(): boolean {
    this._muted = !this._muted;
    if (this._muted) this.stop();
    return this._muted;
  }

  get isMuted(): boolean {
    return this._muted;
  }

  get hasLastText(): boolean {
    return Boolean(this._lastText);
  }
}
