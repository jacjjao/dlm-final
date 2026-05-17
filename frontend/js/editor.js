export class Editor {
  /**
   * @param {HTMLElement} codeEl       - <code> element for syntax display
   * @param {HTMLElement} placeholderEl - placeholder shown when empty
   */
  constructor(codeEl, placeholderEl) {
    this._codeEl = codeEl;
    this._placeholderEl = placeholderEl;
    this._code = '';
  }

  /** Display code with syntax highlighting. */
  setCode(code) {
    this._code = code;
    // Reset highlight.js state before re-highlighting
    this._codeEl.removeAttribute('data-highlighted');
    this._codeEl.textContent = code;
    hljs.highlightElement(this._codeEl);
    this._placeholderEl.style.display = 'none';
  }

  getCode() {
    return this._code;
  }

  clear() {
    this._code = '';
    this._codeEl.removeAttribute('data-highlighted');
    this._codeEl.textContent = '';
    this._placeholderEl.style.display = '';
  }

  isEmpty() {
    return this._code.trim().length === 0;
  }
}
