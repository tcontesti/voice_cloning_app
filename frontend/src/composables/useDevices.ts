import { ref, onMounted, onUnmounted } from 'vue'

export function useAudioInputDevices() {
  const devices = ref<MediaDeviceInfo[]>([])
  const error = ref<string | null>(null)

  async function refresh() {
    try {
      // labels are empty until we have at least one mic permission grant
      const all = await navigator.mediaDevices.enumerateDevices()
      devices.value = all.filter((d) => d.kind === 'audioinput')
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  function onDeviceChange() { void refresh() }

  onMounted(() => {
    void refresh()
    navigator.mediaDevices?.addEventListener('devicechange', onDeviceChange)
  })
  onUnmounted(() => {
    navigator.mediaDevices?.removeEventListener('devicechange', onDeviceChange)
  })

  return { devices, error, refresh }
}
