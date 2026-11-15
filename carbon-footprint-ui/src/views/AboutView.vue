<template>
  <div class="ml-20 min-h-screen">
    <BreadcrumbsBar class="pt-4" />
    <div class="prose mt-8">
      <h1>About</h1>
      <p>
        This tool was developed as part of the master thesis <i>Visual Analytics on Digital
        Product Passports to Optimize Production Chains</i> by <b>Moritz Bock</b> as part of the
        CLiCE-DiPP research project funded by the German Federal Ministry for Economic Affairs
        and Climate Action.
      </p>
      <p>
        The tool is continued as <i>DPPviewer</i> by <b>Dirk Burkhardt</b> and the
        <a href="https://vis.h-da.de" target="_blank" rel="noopener noreferrer">VIS team</a> at the Darmstadt University
        of Applied Sciences.
      </p>
      <h2>Version</h2>
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
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import BreadcrumbsBar from '@/components/BreadcrumbsBar.vue'
import { type ApiStatus, fetchApiStatus, isCompatibleApi, requiredApiMajor, uiVersion } from '@/lib/version'

const apiStatus = ref<ApiStatus | null | undefined>(undefined)

onMounted(async () => {
  apiStatus.value = (await fetchApiStatus()) ?? null
})
</script>
