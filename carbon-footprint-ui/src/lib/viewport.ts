/**
 * Small screens (phones) get a reduced presentation: search, asset list and a compact single asset view. The
 * complex analyses (component tree, Sankey, Compare, Datasheet, simulation) are made for larger screens.
 */
import { useMediaQuery } from '@vueuse/core'
import { ref } from 'vue'

/** Below Tailwind's md breakpoint (768 px) */
export const isMobile = useMediaQuery('(max-width: 767px)')

/** The user chose to open a desktop analysis on a small screen anyway (for this session) */
export const showDesktopViewsAnyway = ref(false)
