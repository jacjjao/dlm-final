export class Editor {
  private readonly _cm: CodeMirror.EditorFromTextArea;

  constructor(el: HTMLTextAreaElement) {
    this._cm = CodeMirror.fromTextArea(el, {
      mode: 'python',
      theme: 'monokai',
      lineNumbers: true,
      indentUnit: 4,
      tabSize: 4,
      indentWithTabs: false,
      lineWrapping: false,
      autofocus: false,
    });
  }

  setCode(code: string): void {
    this._cm.setValue(code);
  }

  getCode(): string {
    return this._cm.getValue();
  }

  clear(): void {
    this._cm.setValue('');
  }

  isEmpty(): boolean {
    return this._cm.getValue().trim().length === 0;
  }

  onChange(callback: () => void): void {
    this._cm.on('change', callback);
  }
}
