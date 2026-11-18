/**
 * Temporary uploads of AAS/AASX files (API endpoints /uploads).
 *
 * Uploads are referenced like external files by a pseudo URL "upload:<id>" in the route parameter "preload", so
 * links to analyses of uploaded files work for others as long as the upload exists on the server.
 */
import { reactive } from 'vue'
import apiConfig from '@/lib/apiConfig'
import type { components } from '@/lib/api/AssetAdministrationShellRepository'

type Shell = components['schemas']['AssetAdministrationShell']

export const UPLOAD_URL_PREFIX = 'upload:'

export type UploadLimits = {
  enabled: boolean
  maxBytes: number
  ttlSeconds: number
}

export type UploadInfo = {
  id: string
  filename: string
  size: number
  createdAt: string
  expiresAt: string
}

export type Upload = UploadInfo & { shells: Shell[] }

/** Error with the HTTP status of the failed request, like the errors of openapi-fetch. */
export class UploadRequestError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

/** File name and expiry of the uploads known to this browser session, keyed by upload id. */
export const uploadInfos = reactive<Record<string, UploadInfo>>({})

export function isUploadUrl(url: string): boolean {
  return url.startsWith(UPLOAD_URL_PREFIX)
}

export function uploadUrl(id: string): string {
  return UPLOAD_URL_PREFIX + id
}

export function uploadIdFromUrl(url: string): string {
  return url.substring(UPLOAD_URL_PREFIX.length)
}

function endpoint(path: string): string | null {
  const base = apiConfig.assetAdministrationShellAdditionalsUrl.trim()
  return base ? `${base.replace(/\/+$/, '')}${path}` : null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = endpoint(path)
  if (!url) {
    throw new UploadRequestError(0, 'Uploads are not available because no API endpoint for additionals is configured')
  }
  const response = await fetch(url, init)
  if (!response.ok) {
    let message = response.statusText
    try {
      message = (await response.json()).message ?? message
    } catch {
      // body is not JSON, keep the status text
    }
    throw new UploadRequestError(response.status, message)
  }
  return (response.status === 204 ? undefined : await response.json()) as T
}

function remember(upload: Upload): Upload {
  const { shells: _shells, ...info } = upload
  uploadInfos[upload.id] = info
  return upload
}

let limitsRequest: Promise<UploadLimits | null> | undefined

/** Limits as reported by the API (also when uploads are disabled), null if the API has no such endpoint. */
export function fetchRawUploadLimits(): Promise<UploadLimits | null> {
  limitsRequest ??= request<UploadLimits>('/uploads').catch(() => null)
  return limitsRequest
}

/** Maximum size and retention of uploads, null if the API offers no uploads. */
export async function fetchUploadLimits(): Promise<UploadLimits | null> {
  const limits = await fetchRawUploadLimits()
  return limits?.enabled ? limits : null
}

export async function uploadFile(file: File): Promise<Upload> {
  const upload = await request<Upload>(`/uploads?filename=${encodeURIComponent(file.name)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/octet-stream' },
    body: file,
  })
  return remember(upload)
}

export async function fetchUpload(id: string): Promise<Upload> {
  return remember(await request<Upload>(`/uploads/${encodeURIComponent(id)}`))
}

export async function deleteUpload(id: string): Promise<void> {
  delete uploadInfos[id]
  try {
    await request<void>(`/uploads/${encodeURIComponent(id)}`, { method: 'DELETE' })
  } catch (e) {
    // already expired or removed: nothing left to delete
    if (!(e instanceof UploadRequestError && e.status === 404)) {
      throw e
    }
  }
}

/** File size for messages, e.g. "25 MB". */
export function formatMegabytes(bytes: number): string {
  const mb = bytes / (1024 * 1024)
  return `${Number.isInteger(mb) ? mb : mb.toFixed(1)} MB`
}
