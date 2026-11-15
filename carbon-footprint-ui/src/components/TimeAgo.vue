<template>
  <span>{{ timeString }}</span>
</template>
<script lang="ts" setup>
import { onUnmounted, ref } from 'vue'

/**
 * small component which shows a certain time ago and updates it every <interval, default=5000> milliseconds
 */
const props = withDefaults(
  defineProps<{
    interval?: number
    date?: Date
  }>(),
  { interval: 5000, date: undefined }
)

/**
 * Current string representation of the duration
 */
const timeString = ref('just now')
const date = props.date || new Date();

/**
 * Update the duration every interval
 */
const updateTime = setInterval(() => {
  const diff = Math.round((Date.now() - date.getTime()) / 1000)
  const seconds = diff % 60
  const minutes = Math.floor(diff / 60)
  if (diff == 0) {
    return 'just now'
  }
  let newTime = ''
  if (minutes) {
    newTime += minutes + ' minute'
    if (minutes != 1) {
      newTime += 's'
    }
  }
  if (seconds || !minutes) {
    if (minutes) {
      newTime += ' and '
    }
    newTime += seconds + ' second'
    if (seconds != 1) {
      newTime += 's'
    }
    newTime += ' '
  }
  timeString.value = newTime + ' ago'
}, props.interval)

// Delete the interval method when the not shown anymore
onUnmounted(() => {
  clearInterval(updateTime)
})
</script>
