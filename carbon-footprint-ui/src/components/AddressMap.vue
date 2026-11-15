<template>
  <div class="relative flex-1">
    <div ref="mapContainer" class="h-full w-full" :class="{ 'map-dark': darkMode }"></div>
    <div
      v-if="notFound"
      class="absolute bottom-2 left-2 z-[1000] rounded-sm bg-base-100/80 px-2 py-1 text-sm"
    >
      Address could not be located
    </div>
  </div>
</template>

<script setup lang="ts">
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import { inject, onBeforeUnmount, onMounted, type Ref, ref, watch } from 'vue'
import { darkModeKey } from '@/lib/injectionKeys'
import apiConfig from '@/lib/apiConfig'
import { geocode, type LatLng } from '@/lib/geo/geocoding'

const props = defineProps<{
  street?: string
  city?: string
  stateCounty?: string
  zipcode?: string
  countryCode?: string
}>()

const DEFAULT_CENTER: LatLng = [47.636, 9.389]
const DEFAULT_ZOOM = 5
const ADDRESS_ZOOM = 14

// Die Standard-Markerbilder von Leaflet werden vom Bundler sonst nicht gefunden
const icon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
})

const mapContainer = ref<HTMLDivElement>()
const darkMode = inject<Ref<boolean>>(darkModeKey, ref(false))
const notFound = ref(false)

let map: L.Map | undefined
let marker: L.Marker | undefined
let resizeObserver: ResizeObserver | undefined
let lastRequest = 0

onMounted(() => {
  if (!mapContainer.value) {
    return
  }
  map = L.map(mapContainer.value, { center: DEFAULT_CENTER, zoom: DEFAULT_ZOOM, scrollWheelZoom: false })
  L.tileLayer(apiConfig.mapTileUrl, { maxZoom: 19, attribution: apiConfig.mapAttribution }).addTo(map)
  resizeObserver = new ResizeObserver(() => map?.invalidateSize())
  resizeObserver.observe(mapContainer.value)
  void locate()
})

async function locate() {
  const request = ++lastRequest
  const position = await geocode({
    street: props.street,
    city: props.city,
    state: props.stateCounty,
    postalCode: props.zipcode,
    countryCode: props.countryCode
  })
  if (request !== lastRequest || !map) {
    return // veraltete Antwort oder Komponente bereits entfernt
  }
  marker?.remove()
  marker = undefined
  notFound.value = !position
  if (position) {
    map.setView(position, ADDRESS_ZOOM)
    marker = L.marker(position, { icon, keyboard: false }).addTo(map)
  }
}

watch(
  () => [props.street, props.city, props.stateCounty, props.zipcode, props.countryCode],
  () => void locate()
)

function recenter() {
  map?.invalidateSize()
  const position = marker?.getLatLng()
  if (position) {
    map?.setView(position)
  }
}

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  map?.remove()
  map = undefined
})

defineExpose({
  recenter
})
</script>

<style scoped>
/* OpenStreetMap bietet keine dunklen Kacheln; im Dunkelmodus werden sie per Filter abgedunkelt */
.map-dark :deep(.leaflet-tile-pane) {
  filter: invert(1) hue-rotate(180deg) brightness(0.95) contrast(0.9);
}
.map-dark :deep(.leaflet-control-attribution) {
  background: rgb(0 0 0 / 0.6);
  color: #ddd;
}
.map-dark :deep(.leaflet-control-attribution a) {
  color: #9cf;
}
</style>
