<template>
  <div class="prose max-w-none">
    <h2 class="mt-0">About</h2>
    <p>
      This tool was developed as part of the master thesis <i>Visual Analytics on Digital
      Product Passports to Optimize Production Chains</i> by <b>Moritz Bock</b> as part of the
      CLiCE-DiPP research project funded by the German Federal Ministry for Economic Affairs
      and Climate Action.
    </p>
    <p>
      The tool is continued as <i>DPPviewer</i> by <b>Dirk Burkhardt</b> and the
      <a href="https://vis.h-da.de" target="_blank" rel="noopener noreferrer">VIS team</a> at the Darmstadt University
      of Applied Sciences. The tool is available on <a href="https://github.com/dirk-burkhardt/dpp-carbon-footprint-viewer" target="_blank">GitHub</a>.
    </p>
    <h3>Version</h3>
    <table>
      <tbody>
        <tr>
          <th>User interface</th>
          <td>{{ uiVersion }}</td>
        </tr>
        <tr>
          <th>API</th>
          <td>
            <template v-if="apiStatus">
              {{ apiStatus.version }}
              <span v-if="!isCompatibleApi(apiStatus.version)" class="text-error">
                (not compatible, API {{ requiredApiMajor }}.x required)
              </span>
</template>
          <template v-else-if="apiStatus === null">not reachable</template>
          <template v-else>&hellip;</template>
        </td>
      </tr>
    </tbody>
  </table>
</div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { type ApiStatus, fetchApiStatus, isCompatibleApi, requiredApiMajor, uiVersion } from '@/lib/version'

const apiStatus = ref<ApiStatus | null | undefined>(undefined)

onMounted(async () => {
  apiStatus.value = (await fetchApiStatus()) ?? null
})
</script>
