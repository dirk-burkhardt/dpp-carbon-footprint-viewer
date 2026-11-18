/**
 * Normalized product data from the DPPviewer API (endpoints /products/...).
 *
 * The API parses all known versions of the IDTA submodel templates (e.g. Carbon Footprint 0.9 and 1.0 to 1.0.x,
 * battery passport). The UI uses these results instead of reading the submodels itself. Other AAS servers do not
 * offer these endpoints; callers then fall back to their own parsing.
 */
import apiConfig from '@/lib/apiConfig'
import { encodeId } from '@/lib/encoding'
import { ErrorClient } from '@/lib/ErrorDataHandler'
import { LifeCyclePhases } from '@/lib/lifeCycleUtil'
import type { CarbonFootprintType, GoodsAddress } from '@/lib/model/CarbonFootprintType'

export type ApiAddress = {
  street?: string | null
  houseNumber?: string | null
  zipcode?: string | null
  cityTown?: string | null
  stateCounty?: string | null
  country?: string | null
  latitude?: number | null
  longitude?: number | null
}

export type ApiFootprint = {
  kind: 'product' | 'transport'
  templateVersion: string
  submodelId?: string | null
  idShortPath?: string | null
  calculationMethods: string[]
  co2eq?: number | null
  referenceUnit?: string | null
  quantity?: number | null
  lifeCyclePhases: string[]
  transportProcess?: 'WTT' | 'TTW' | 'WTW' | null
  goodsHandoverAddress?: ApiAddress | null
  goodsTakeoverAddress?: ApiAddress | null
  publicationDate?: string | null
  expirationDate?: string | null
  warnings: string[]
}

export type ApiCarbonFootprintResult = {
  footprints: ApiFootprint[]
}

const cache = new Map<string, Promise<ApiCarbonFootprintResult | null>>()

/**
 * Carbon footprints of a shell as parsed by the API, null if the API does not offer the endpoint (or fails).
 * Results are cached per shell.
 */
export function fetchCarbonFootprint(aasIdentifier: string): Promise<ApiCarbonFootprintResult | null> {
  let result = cache.get(aasIdentifier)
  if (!result) {
    const base = apiConfig.assetAdministrationShellRepositoryUrl.replace(/\/+$/, '')
    result = fetch(`${base}/products/${encodeId(aasIdentifier)}/carbon-footprint`)
      .then((response) => (response.ok ? (response.json() as Promise<ApiCarbonFootprintResult>) : null))
      .catch(() => null)
    cache.set(aasIdentifier, result)
    // Do not keep failures, a later call may succeed
    result.then((r) => r ?? cache.delete(aasIdentifier))
  }
  return result
}

function toAddress(address?: ApiAddress | null): GoodsAddress {
  return {
    street: address?.street ?? undefined,
    houseNumber: address?.houseNumber ?? undefined,
    zipcode: address?.zipcode ?? undefined,
    cityTown: address?.cityTown ?? undefined,
    country: address?.country ?? undefined,
    latitude: address?.latitude ?? undefined,
    longitude: address?.longitude ?? undefined,
  }
}

function toDate(value?: string | null): Date | undefined {
  if (!value) {
    return undefined
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? undefined : date
}

const TRANSPORT_PROCESS = {
  WTT: 'WTT - Well-to-Tank',
  TTW: 'TTW - Tank-to-Wheel',
  WTW: 'WTW - Well-to-Wheel',
} as const

/** Warning texts of the API are German; the one the UI showed before keeps its English wording */
function reportWarnings(footprint: ApiFootprint, source: string) {
  const subject = footprint.idShortPath ?? undefined
  for (const warning of footprint.warnings) {
    if (footprint.kind === 'transport' && footprint.transportProcess === 'WTW' && warning.includes('Well-to-Tank')) {
      ErrorClient.warn(
        'The asset does not specify whether its calculations encompass Well-to-Tank, Tank-to-Wheel, or both',
        'The value of TCFProcessesForGreenhouseGasEmissionInATransportService does not exist, therefore the analysis handles the missing value as Well-to-Wheel',
        { source, subject },
      )
    } else {
      ErrorClient.warn('The carbon footprint contains incomplete or unusual values', warning, { source, subject })
    }
  }
}

/**
 * Converts the API result into the structure the visualizations use.
 * @param result API result
 * @param source name of the asset, used to attribute warnings
 */
export function toCarbonFootprintType(result: ApiCarbonFootprintResult, source: string): CarbonFootprintType {
  const carbonFootprint: CarbonFootprintType = { product: [], transport: [] }
  for (const fp of result.footprints) {
    reportWarnings(fp, source)
    const common = {
      co2eq: fp.co2eq ?? 0,
      referenceValueForCalculation: fp.referenceUnit ?? '',
      quantityOfMeasureForCalculation: fp.quantity ?? 1,
      publicationDate: toDate(fp.publicationDate),
      expirationDate: toDate(fp.expirationDate),
    }
    if (fp.kind === 'product') {
      carbonFootprint.product.push({
        ...common,
        calculationMethod: new Set(fp.calculationMethods),
        lifeCyclePhase: new LifeCyclePhases(fp.lifeCyclePhases),
        goodsAddressHandover: toAddress(fp.goodsHandoverAddress),
      })
    } else {
      carbonFootprint.transport.push({
        ...common,
        calculationMethod: fp.calculationMethods.join(', '),
        processesForGreenhouseGasEmissionInATransportService: TRANSPORT_PROCESS[fp.transportProcess ?? 'WTW'],
        goodsTransportAddressTakeover: toAddress(fp.goodsTakeoverAddress),
        goodsTransportAddressHandover: toAddress(fp.goodsHandoverAddress),
      })
    }
  }
  return carbonFootprint
}

export type ApiMeasureSource = {
  submodelId?: string | null
  path: string[]
  idShort?: string | null
  name?: string | null
  semanticId?: string | null
  value?: string | null
  unit?: string | null
}

export type ApiMeasure = {
  /** Value in the SI unit: kg, W, m or a (years) */
  value: number
  unit: string
  source: ApiMeasureSource
}

/** Reference quantities of a product from Technical Data (endpoint /products/{id}/indicators) */
export type ApiIndicators = {
  mass?: ApiMeasure | null
  power?: ApiMeasure | null
  lifetime?: ApiMeasure | null
  width?: ApiMeasure | null
  height?: ApiMeasure | null
  depth?: ApiMeasure | null
  volume?: number | null
  materials: { name: string, value: string, source: ApiMeasureSource }[]
  warnings: string[]
}

const indicatorCache = new Map<string, Promise<ApiIndicators | null>>()

/** Reference quantities of a shell, null if the API does not offer them. Cached per shell. */
export function fetchIndicators(aasIdentifier: string): Promise<ApiIndicators | null> {
  let result = indicatorCache.get(aasIdentifier)
  if (!result) {
    const base = apiConfig.assetAdministrationShellRepositoryUrl.replace(/\/+$/, '')
    result = fetch(`${base}/products/${encodeId(aasIdentifier)}/indicators`)
      .then((response) => (response.ok ? (response.json() as Promise<ApiIndicators>) : null))
      .catch(() => null)
    indicatorCache.set(aasIdentifier, result)
    result.then((r) => r ?? indicatorCache.delete(aasIdentifier))
  }
  return result
}

/** Short description of where a value comes from, e.g. for a tooltip */
export function describeSource(measure: ApiMeasure): string {
  const { source } = measure
  const name = source.name || source.idShort || 'property'
  const given = [source.value, source.value && source.unit && !source.value.includes(source.unit) ? source.unit : '']
    .filter(Boolean)
    .join(' ')
  return `Technical Data: ${[...source.path, name].join(' › ')} = ${given}`
}
