import { CircularDependencyError } from '@/lib/visualization/CarbonSankeyData'

/**
 * Error response data
 */
export type ErrorDataHandler = {
  /**
   * Timestamp of the error
   */
  timestamp?: Date

  /**
   * Error (i.e. HTTP) status code
   */
  status?: number

  /**
   * Information on the error
   */
  message: string

  /**
   * Severity, errors by default
   */
  level?: 'error' | 'warning'

  /**
   * More details on the error
   */
  details?: string

  /**
   * stack trace of the error
   */
  trace?: string
}

/**
 * ErrorClient handling errors from the beginning and making it able to show the UI even though an error might
 * occur before the UI is loaded
 */
export class ErrorClient {
  /**
   * Whether an error handler was registered
   * @private
   */
  private static registered = false

  /**
   * Pending errors which occured before a handler was registered
   * @private
   */
  private static pendingErrors: ErrorDataHandler[] = []

  /**
   * Set the error handler
   * @param newErrorFunction new error handler
   */
  static set errorFunction (newErrorFunction: (e: ErrorDataHandler) => void) {
    if (ErrorClient.registered) {
      ErrorClient.add({
        timestamp: new Date(),
        message: 'ErrorClient already registered'
      })
    }
    this.#errorFunction = newErrorFunction;
    // Pass errors which occurred before setting the handler now to it
    while (ErrorClient.pendingErrors.length) {
      this.#errorFunction(ErrorClient.pendingErrors.shift()!)
    }
    this.registered = true
  }

  static #errorFunction = (e: ErrorDataHandler) => {
    this.pendingErrors.push(e);
  }

  /**
   * Add an unknown error object
   * @param error Error to add
   */
  static addUnknown (error: unknown) {
    let details: string | undefined;
    try {
      details = JSON.stringify(error);
    } catch (exc) {
      if (!(exc instanceof CircularDependencyError)) {
        throw exc;
      }
    }
    ErrorClient.add({
      timestamp: new Date(),
      message: `Error of unknown type: ${(error || JSON.stringify(error)).toString()}`,
      details
    })
  }

  /**
   * Add an error to handle
   * @param error Error to add
   */
  static add (error: ErrorDataHandler | undefined | string) {
    if (error === undefined) {
      return
    }
    if (typeof error === 'string') {
      error = {
        message: error,
      }
    }
    if (!error.timestamp) {
      error.timestamp = new Date();
    }
    this.#errorFunction(error);
  }

  /**
   * Add a warning (a problem that does not prevent the display, e.g. incomplete data)
   * @param message short description
   * @param details further information
   */
  static warn (message: string, details?: string) {
    ErrorClient.add({ message, details, level: 'warning' })
  }

  /**
   * Add an error from an API call to handle
   * @param apiResponse api response containing an error
   */
  static addFromApi (apiResponse?: { [key: string]: unknown }) {
    if (!apiResponse) return
    ErrorClient.add({
      timestamp: new Date(apiResponse?.timestamp as string),
      message: (apiResponse?.error as string) || (apiResponse?.message as string),
      details: apiResponse.error ? (apiResponse?.message as string) : undefined,
      status: apiResponse?.status as number,
      trace: apiResponse?.trace as string
    })
  }

  static unhandledRejection(event: PromiseRejectionEvent) {
    const reason = event.reason
    let message = 'Unexpected error'
    let trace: string | undefined
    if (reason instanceof Error) {
      message = reason.message || message
      trace = reason.stack
    } else if (typeof reason === 'string') {
      message = reason
    } else if (reason && typeof reason === 'object') {
      const r = reason as { message?: unknown, status?: unknown }
      message = typeof r.message === 'string' ? r.message : message
      try {
        trace = JSON.stringify(reason)
      } catch {
        trace = undefined
      }
    }
    ErrorClient.add({
      timestamp: new Date(performance.timeOrigin + event.timeStamp),
      message,
      status: typeof reason?.status === 'number' ? reason.status : undefined,
      trace,
    })
  }
}
