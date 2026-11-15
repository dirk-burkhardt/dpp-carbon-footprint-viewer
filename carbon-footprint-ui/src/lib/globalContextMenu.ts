
export type ContextMenuEntry = {
  label: string;
  data?: Record<string, unknown>;
  onEvent?: (e: MouseEvent, data: ContextMenuEntry["data"]) => any;
  triggerEvent?: string;
}

type Event = MouseEvent | { pageX: number; pageY: number };

export default class GlobalContextMenu {
  static #showMethod?: (e: Event, entries: ContextMenuEntry[], onClose?: (e?: Event) => void) => any;

  static #hideMethod?: (e?: Event) => any;

  static #entries: ContextMenuEntry[] = [];

  static #event?: Event;

  static #onClose?: (e?: Event) => void;

  static show(e: Event, entries: ContextMenuEntry[], onClose?: (e?: Event) => void): void {
    if (entries.length === 0) {
      return;
    }
    if (GlobalContextMenu.#showMethod) {
      GlobalContextMenu.#showMethod(e, entries);
    } else {
      GlobalContextMenu.#entries = entries;
      GlobalContextMenu.#event = e;
      GlobalContextMenu.#onClose = onClose;
    }
  }

  static hide(e?: Event): void {
    if (GlobalContextMenu.#hideMethod) {
      GlobalContextMenu.#hideMethod(e);
    } else {
      GlobalContextMenu.#entries = [];
      GlobalContextMenu.#event = undefined;
      GlobalContextMenu.#onClose = undefined;
    }
  }

  static register(showMethod: (e: Event, entries: ContextMenuEntry[], onClose?: (e?: Event) => void) => any, hideMethod: (e?: Event) => any): void {
    GlobalContextMenu.#showMethod = showMethod;
    GlobalContextMenu.#hideMethod = hideMethod;
    if (GlobalContextMenu.#entries.length !== 0 && GlobalContextMenu.#event) {
      showMethod(GlobalContextMenu.#event, GlobalContextMenu.#entries, GlobalContextMenu.#onClose);
    }
    GlobalContextMenu.#entries = [];
    GlobalContextMenu.#event = undefined;
    GlobalContextMenu.#onClose = undefined;
  }
}
