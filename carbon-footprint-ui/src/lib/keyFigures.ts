/**
 * Key figures that put the carbon footprint into context:
 *
 * - intensities: CO2eq per kg or per watt, using reference quantities from Technical Data
 * - analysis of the product structure (Hierarchical Structures): own manufacturing versus purchased components,
 *   data coverage of the components and the components causing most of the emissions (hotspots)
 *
 * Everything is derived from declared values only; nothing is estimated here.
 */
import type CarbonTree from '@/lib/model/CarbonTree'
import type { ApiIndicators, ApiMeasure } from '@/lib/api/products'

export type ReferenceQuantity = 'mass' | 'power'

export const referenceLabels: Record<ReferenceQuantity, { per: string, unit: string, name: string }> = {
  mass: { per: 'per kg', unit: 'kg', name: 'mass' },
  power: { per: 'per W', unit: 'W', name: 'power' },
}

/** CO2eq per unit of the reference quantity, undefined if the quantity is unknown or zero */
export function intensity(co2eq: number | undefined, measure: ApiMeasure | null | undefined): number | undefined {
  if (co2eq === undefined || !measure || measure.value <= 0) {
    return undefined
  }
  return co2eq / measure.value
}

export function referenceMeasure(indicators: ApiIndicators | null | undefined, quantity: ReferenceQuantity) {
  return indicators?.[quantity] ?? undefined
}

export type Hotspot = {
  tree: CarbonTree
  name: string
  /** Number of units within the whole product */
  units: number
  depth: number
  /** Emissions caused by this component itself (without its own components), all units together, kg */
  co2eq: number
  share: number
  cumulativeShare: number
  /** Belongs to the components that together cause the first 80 % of the emissions */
  isHotspot: boolean
}

export type StructureAnalysis = {
  /** Product emissions of the asset itself (its own manufacturing), kg; 0 if the asset only sums up components */
  ownProductCo2eq: number
  /** Product emissions of all components (including their transports), kg */
  componentsProductCo2eq: number
  /** Leaf components (counted with their units) and how many of them have an own carbon footprint */
  leafComponents: number
  leafComponentsWithFootprint: number
  coverage: number | undefined
  depth: number
  hotspots: Hotspot[]
}

export const HOTSPOT_SHARE = 0.8

/**
 * Analyses the product structure of an asset.
 *
 * The emissions of each node are split into the part it causes itself (its declared footprint minus the
 * footprints of its components, see CarbonTree.assetProductCo2eq) and the part of its components. Summing up the
 * own parts of all nodes, multiplied with their number of units, gives the total again.
 */
export function analyzeStructure(tree: CarbonTree): StructureAnalysis {
  let leafComponents = 0
  let leafComponentsWithFootprint = 0
  let depth = 0
  const contributions: Omit<Hotspot, 'share' | 'cumulativeShare' | 'isHotspot'>[] = []
  tree.forEach((node, _i, level, units) => {
    depth = Math.max(depth, level)
    const own = Math.max(0, node.assetProductCo2eq ?? 0) + Math.max(0, node.assetTransportCo2eq ?? 0)
    if (level > 0) {
      if (node.connectionsArray.length === 0) {
        leafComponents += units
        if (node.asset.footprint) {
          leafComponentsWithFootprint += units
        }
      }
    }
    // The asset itself is listed too: its own manufacturing and transport can be the largest single source
    if (own > 0) {
      const name = level === 0 ? `${node.name} (own manufacturing and transport)` : node.name
      contributions.push({ tree: node, name, units, depth: level, co2eq: own * units })
    }
  })
  const total = contributions.reduce((s, c) => s + c.co2eq, 0)
  let cumulative = 0
  const hotspots = contributions
    .sort((a, b) => b.co2eq - a.co2eq)
    .map((c) => {
      const share = total > 0 ? c.co2eq / total : 0
      // A component is a hotspot if the components before it have not yet reached the threshold
      const isHotspot = cumulative < HOTSPOT_SHARE
      cumulative += share
      return { ...c, share, cumulativeShare: cumulative, isHotspot }
    })
  const componentsProductCo2eq = Math.max(0, tree.childrenProductCo2eq ?? 0)
  return {
    ownProductCo2eq: Math.max(0, tree.assetProductCo2eq ?? 0),
    componentsProductCo2eq,
    leafComponents,
    leafComponentsWithFootprint,
    coverage: leafComponents > 0 ? leafComponentsWithFootprint / leafComponents : undefined,
    depth,
    hotspots,
  }
}
