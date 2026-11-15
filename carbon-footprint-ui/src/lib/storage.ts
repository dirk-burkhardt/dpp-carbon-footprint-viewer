import { ref, watch } from "vue";

// Präfix bleibt aus Kompatibilität (gespeicherte Favoriten und Einstellungen) beim alten Namen
const DEFAULT_PREFIX = "carbon-trace"

function localStorageKey(key: string, space: string, prefix: string) {
  if (prefix && !prefix.endsWith(":")) {
    prefix += ":";
  }
  if (space && !space.endsWith(":")) {
    space += ":";
  }
  return prefix + space + key;
}

export function getLocalStorage<Type>(
  key: string,
  defaultValue: Type,
  space = "",
  prefix = DEFAULT_PREFIX
) {
  let item: string | null = null;
  try {
    item = localStorage.getItem(localStorageKey(key, space, prefix));
  } catch {
    return defaultValue;
  }
  if (item === null) {
    return defaultValue;
  }
  try {
    return JSON.parse(item as string) as Type;
  } catch {
    console.warn(
      `localStorage of ${prefix}${space}${key} was not valid JSON. Falling back to defaultValue.`
    );
  }
  return defaultValue;
}

export function setLocalStorage<Type>(
  key: string,
  value: Type,
  space = "",
  prefix = DEFAULT_PREFIX
) {
  try {
    localStorage.setItem(localStorageKey(key, space, prefix), JSON.stringify(value));
  } catch (error) {
    // Speicher voll oder im privaten Modus nicht verfügbar: Einstellung gilt dann nur für diese Sitzung
    console.warn(`localStorage ${prefix}${space}${key} konnte nicht gespeichert werden`, error);
  }
}

/**
 * Ref which saves its status in the localStorage.
 */
export function storageRef<Type>(
  key: string,
  defaultValue: Type,
  space = "",
  prefix = DEFAULT_PREFIX
) {
  const reference = ref(getLocalStorage(key, defaultValue, space, prefix));

  watch(
    reference,
    (newValue) => {
      setLocalStorage(key, newValue, space, prefix);
    },
    { deep: true }
  );

  return reference;
}

const UNDEFINED = Object();
const objectIds = new WeakMap<object, number>();
let nextObjectId = 0;

/** Eindeutiger Schlüsselteil: Werte über JSON, Objekte (z. B. Promises) über ihre Identität. */
function cacheKeyPart(arg: unknown): string {
  if (Array.isArray(arg)) {
    return `[${arg.map(cacheKeyPart).join(',')}]`;
  }
  if (arg !== null && (typeof arg === 'object' || typeof arg === 'function')) {
    let id = objectIds.get(arg);
    if (id === undefined) {
      id = ++nextObjectId;
      objectIds.set(arg, id);
    }
    return `#${id}`;
  }
  return arg === undefined ? 'undefined' : JSON.stringify(arg);
}

/**
 * Merkt sich das Ergebnis einer Methode je Argumentliste. Abgelehnte Promises werden wieder entfernt,
 * damit ein vorübergehender Fehler (z. B. Netzwerk) beim nächsten Aufruf erneut versucht wird.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function cached(_target: any, _propertyKey: string, descriptor: PropertyDescriptor): typeof descriptor.value {
  const originalMethod = descriptor.value;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const methodCache: WeakMap<any, Map<string, unknown>> = new WeakMap()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  descriptor.value = function cache(this: any, ...args: unknown[]) {
    const key = args.map(cacheKeyPart).join(',');
    let cacheValue = methodCache.get(this);
    if (cacheValue?.has(key)) {
      const value = cacheValue.get(key);
      return value === UNDEFINED ? undefined : value;
    }
    const val = originalMethod.apply(this, args);
    if (cacheValue === undefined) {
      cacheValue = new Map()
      methodCache.set(this, cacheValue)
    }
    const store = cacheValue;
    store.set(key, val === undefined ? UNDEFINED : val);
    if (val instanceof Promise) {
      val.catch(() => {
        if (store.get(key) === val) {
          store.delete(key);
        }
      });
    }
    return val;
  };
  return descriptor;
}
