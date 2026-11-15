/**
 * Fehler beim Laden der Assets einer Ansicht.
 *
 * Ein Fehler wird der Route zugeordnet, auf der das Laden begonnen hat. So erscheint er nur in dieser Ansicht
 * (als Hinweis anstelle des Inhalts), auch wenn die Anfrage erst nach einem Seitenwechsel scheitert. Zusätzlich
 * landet er in der Fehlerliste der Statusanzeige.
 */
import { computed, reactive } from 'vue'
import router from '@/router'
import { ErrorClient } from '@/lib/ErrorDataHandler'

type Message = string | [string] | [string, string]
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type MessageFactory = (reason: any) => Message | false

/** Fehlermeldungen je Routenpfad */
const loadErrors = reactive<Record<string, string>>({})

// Beim Verlassen einer Ansicht deren Fehler vergessen, beim erneuten Aufruf wird neu geladen
router.afterEach((to, from) => {
  if (to.fullPath !== from.fullPath) {
    delete loadErrors[from.fullPath]
  }
})

/** Fehlermeldung der aktuellen Ansicht, undefined wenn alles geladen werden konnte */
export const currentLoadError = computed(() => loadErrors[router.currentRoute.value.fullPath])

export class BackOnErrorHandler {
  /**
   * Meldet einen Fehler des Promises für die aktuelle Ansicht.
   * @param promise Ladevorgang
   * @param message Meldung oder Funktion, die aus dem Fehler eine Meldung erzeugt (false: nicht melden)
   */
  static bind<T> (promise: Promise<T>, message?: Message | MessageFactory): Promise<T> {
    const path = router.currentRoute.value.fullPath
    promise.catch((reason) => {
      let resolved: Message | false = message === undefined ? 'An error occurred' : (message as Message)
      if (typeof message === 'function') {
        resolved = message(reason)
      }
      if (resolved === false) {
        return
      }
      const [title] = typeof resolved === 'string' ? [resolved] : resolved
      ErrorClient.add({
        message: title,
        details: reason instanceof Error ? reason.message : (reason?.message ?? undefined),
        status: typeof reason?.status === 'number' ? reason.status : undefined,
        trace: reason instanceof Error ? reason.stack : undefined,
      })
      // Nur merken, wenn die Ansicht noch angezeigt wird
      if (router.currentRoute.value.fullPath === path) {
        loadErrors[path] = title
      }
    })
    return promise
  }
}
