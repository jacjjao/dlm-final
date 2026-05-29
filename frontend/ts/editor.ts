export class Editor {
  private readonly _el: HTMLTextAreaElement;

  constructor(el: HTMLTextAreaElement) {
    this._el = el;
  }

  setCode(code: string): void {
    this._el.value = code;
  }

  getCode(): string {
    return this._el.value;
  }

  clear(): void {
    this._el.value = '';
  }

  isEmpty(): boolean {
    return this._el.value.trim().length === 0;
  }
}
