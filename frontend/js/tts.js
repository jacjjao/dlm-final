export class TTS {
  constructor() {
    this._synth = window.speechSynthesis;
    this._muted = false;
    this._lastText = '';
  }

  speak(text) {
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

  stop() {
    this._synth.cancel();
  }

  replay() {
    if (this._lastText) this.speak(this._lastText);
  }

  /** Toggle mute. Returns the new muted state. */
  toggleMute() {
    this._muted = !this._muted;
    if (this._muted) this.stop();
    return this._muted;
  }

  get isMuted() {
    return this._muted;
  }

  get hasLastText() {
    return Boolean(this._lastText);
  }
}
