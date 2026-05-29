declare namespace CodeMirror {
  interface EditorConfiguration {
    mode?: string;
    theme?: string;
    lineNumbers?: boolean;
    indentUnit?: number;
    tabSize?: number;
    indentWithTabs?: boolean;
    lineWrapping?: boolean;
    autofocus?: boolean;
  }

  interface Editor {
    getValue(separator?: string): string;
    setValue(content: string): void;
    on(event: 'change', callback: (instance: Editor) => void): void;
    getWrapperElement(): HTMLElement;
    refresh(): void;
    focus(): void;
  }

  interface EditorFromTextArea extends Editor {
    save(): void;
    getTextArea(): HTMLTextAreaElement;
    toTextArea(): void;
  }

  function fromTextArea(
    host: HTMLTextAreaElement,
    options?: EditorConfiguration,
  ): EditorFromTextArea;
}
