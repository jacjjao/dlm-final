export class Editor {
  private readonly _codeEl: HTMLElement;
  private readonly _placeholderEl: HTMLElement;
  private _code: string = '';

  constructor(codeEl: HTMLElement, placeholderEl: HTMLElement) {
    this._codeEl = codeEl;
    this._placeholderEl = placeholderEl;
  }

  setCode(code: string): void {
    this._code = code;
    this._codeEl.removeAttribute('data-highlighted');
    this._codeEl.textContent = code;
    hljs.highlightElement(this._codeEl);
    this._placeholderEl.style.display = 'none';
  }

  getCode(): string {
    return this._code;
  }

  clear(): void {
    this._code = '';
    this._codeEl.removeAttribute('data-highlighted');
    this._codeEl.textContent = '';
    this._placeholderEl.style.display = '';
  }

  isEmpty(): boolean {
    return this._code.trim().length === 0;
  }
}
