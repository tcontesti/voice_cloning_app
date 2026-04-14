<!--
  DeviceSelector — audio input picker + "upload file" fallback. Persists
  last choice in localStorage. Emits the selected MediaDeviceInfo or a
  File when the user chooses to upload.
-->
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { Mic, Upload, ChevronDown } from 'lucide-vue-next'
import LED from '@/ui/primitives/LED.vue'

const props = withDefaults(
  defineProps<{
    activeDeviceId?: string
    activeLabel?: string
  }>(),
  { activeLabel: '' },
)

const emit = defineEmits<{
  (e: 'selectDevice', info: MediaDeviceInfo): void
  (e: 'uploadFiles', files: FileList): void
}>()

const open = ref(false)
const devices = ref<MediaDeviceInfo[]>([])
const error = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

const STORAGE_KEY = 'studio.audioInput.deviceId'

async function refresh() {
  try {
    const all = await navigator.mediaDevices.enumerateDevices()
    devices.value = all.filter((d) => d.kind === 'audioinput')
  } catch (e) {
    error.value = (e as Error).message
  }
}

function pick(d: MediaDeviceInfo) {
  localStorage.setItem(STORAGE_KEY, d.deviceId)
  emit('selectDevice', d)
  open.value = false
}

function openFiles() {
  fileInput.value?.click()
}
function onFiles(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length) emit('uploadFiles', target.files)
  target.value = ''
  open.value = false
}

function onDocClick(e: MouseEvent) {
  const t = e.target as Node
  if (!t || !(t as Element).closest?.('.studio-devsel')) open.value = false
}

onMounted(() => {
  void refresh()
  navigator.mediaDevices?.addEventListener('devicechange', refresh)
  document.addEventListener('click', onDocClick)
})
onUnmounted(() => {
  navigator.mediaDevices?.removeEventListener('devicechange', refresh)
  document.removeEventListener('click', onDocClick)
})

const activeName = computed(() => {
  if (props.activeLabel) return props.activeLabel
  const d = devices.value.find((x) => x.deviceId === props.activeDeviceId)
  return d?.label || 'Sin dispositivo'
})

defineExpose({ refresh, getStoredId: () => localStorage.getItem(STORAGE_KEY) })
</script>

<template>
  <div class="studio-devsel">
    <button type="button" class="studio-devsel__trigger" @click.stop="open = !open">
      <Mic class="w-4 h-4" />
      <span class="studio-devsel__name">{{ activeName }}</span>
      <LED color="green" :on="!!activeDeviceId" size="xs" />
      <ChevronDown class="w-4 h-4 studio-devsel__chev" :class="{ 'studio-devsel__chev--open': open }" />
    </button>

    <div v-if="open" class="studio-devsel__menu studio-card">
      <div class="studio-devsel__group">
        <div class="studio-label studio-devsel__group-title">Entradas de audio</div>
        <button
          v-for="d in devices"
          :key="d.deviceId"
          type="button"
          class="studio-devsel__item"
          :class="{ 'studio-devsel__item--active': d.deviceId === activeDeviceId }"
          @click="pick(d)"
        >
          <Mic class="w-4 h-4" />
          <span>{{ d.label || `Input ${d.deviceId.slice(0, 6)}` }}</span>
          <LED v-if="d.deviceId === activeDeviceId" color="green" size="xs" />
        </button>
        <p v-if="!devices.length && !error" class="studio-devsel__empty">
          Concede permiso de micrófono para ver los dispositivos.
        </p>
      </div>
      <hr class="studio-divider" />
      <div class="studio-devsel__group">
        <div class="studio-label studio-devsel__group-title">Desde archivo</div>
        <button type="button" class="studio-devsel__item" @click="openFiles">
          <Upload class="w-4 h-4" />
          <span>Subir archivos (WAV · MP3 · FLAC · OGG)</span>
        </button>
      </div>
    </div>

    <input
      ref="fileInput"
      type="file"
      hidden
      multiple
      accept=".wav,.mp3,.flac,.ogg,audio/*"
      @change="onFiles"
    />
  </div>
</template>

<style scoped>
.studio-devsel { position: relative; font-family: var(--font-sans); }
.studio-devsel__trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-radius: var(--radius-4);
  color: var(--fg-0);
  font-size: 13px;
  min-width: 240px;
  transition: border-color var(--dur-base) var(--ease-studio),
              background var(--dur-base) var(--ease-studio);
  cursor: pointer;
}
.studio-devsel__trigger:hover { border-color: var(--line-2); background: var(--bg-3); }
.studio-devsel__name { flex: 1; text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.studio-devsel__chev { transition: transform var(--dur-base) var(--ease-studio); color: var(--fg-2); }
.studio-devsel__chev--open { transform: rotate(180deg); }

.studio-devsel__menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 320px;
  padding: 10px;
  z-index: 40;
}
.studio-devsel__group { display: flex; flex-direction: column; gap: 2px; padding: 4px; }
.studio-devsel__group-title { margin-bottom: 6px; }
.studio-devsel__item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: transparent;
  border: 0;
  border-radius: var(--radius-3);
  color: var(--fg-0);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}
.studio-devsel__item:hover { background: var(--bg-3); }
.studio-devsel__item--active { background: color-mix(in srgb, var(--accent) 14%, transparent); }
.studio-devsel__empty {
  padding: 8px 10px;
  font-size: 12px;
  color: var(--fg-2);
}
</style>
