<!--
  OptionsPanel — slide-in side panel for model parameters. Presents three
  Knobs (stability / similarity / style), a Switch (speaker boost) and a
  minimal select (model variant). v-model:options keeps the shape simple.
-->
<script setup lang="ts">
import { computed } from 'vue'
import Knob from '@/ui/primitives/Knob.vue'
import Switch from '@/ui/primitives/Switch.vue'

export interface ElevenOptions {
  model_id: 'eleven_multilingual_v2' | 'eleven_turbo_v2_5' | 'eleven_v3'
  stability: number
  similarity_boost: number
  style: number
  use_speaker_boost: boolean
}

const MODEL_CHOICES: { value: ElevenOptions['model_id']; label: string; tag?: string }[] = [
  { value: 'eleven_multilingual_v2', label: 'eleven_multilingual_v2' },
  { value: 'eleven_turbo_v2_5', label: 'eleven_turbo_v2_5', tag: 'baja latencia' },
  { value: 'eleven_v3', label: 'eleven_v3', tag: 'preview · más coste' },
]

const props = defineProps<{
  open: boolean
  options: ElevenOptions
}>()

const emit = defineEmits<{
  (e: 'update:options', v: ElevenOptions): void
  (e: 'update:open', v: boolean): void
}>()

function patch<K extends keyof ElevenOptions>(key: K, value: ElevenOptions[K]) {
  emit('update:options', { ...props.options, [key]: value })
}

const modelId = computed({
  get: () => props.options.model_id,
  set: (v: ElevenOptions['model_id']) => patch('model_id', v),
})
</script>

<template>
  <aside class="opts" :class="{ 'opts--open': open }" aria-label="Opciones avanzadas">
    <header class="opts__head">
      <div class="studio-label">OPTIONS · ELEVENLABS</div>
      <button type="button" class="opts__close" aria-label="Cerrar" @click="emit('update:open', false)">×</button>
    </header>

    <div class="opts__group">
      <label class="studio-label" for="opts-model">MODEL</label>
      <select id="opts-model" v-model="modelId" class="input opts__select">
        <option v-for="c in MODEL_CHOICES" :key="c.value" :value="c.value">
          {{ c.label }}{{ c.tag ? ` — ${c.tag}` : '' }}
        </option>
      </select>
    </div>

    <div class="opts__knobs">
      <Knob :model-value="options.stability" :min="0" :max="1" :step="0.01" :default="0.5"
            label="STABILITY" :size="64" :precision="2"
            @update:model-value="(v: number) => patch('stability', v)" />
      <Knob :model-value="options.similarity_boost" :min="0" :max="1" :step="0.01" :default="0.85"
            label="SIMILARITY" :size="64" :precision="2"
            @update:model-value="(v: number) => patch('similarity_boost', v)" />
      <Knob :model-value="options.style" :min="0" :max="1" :step="0.01" :default="0"
            label="STYLE" :size="64" :precision="2"
            @update:model-value="(v: number) => patch('style', v)" />
    </div>

    <div class="opts__group opts__group--switch">
      <Switch
        :model-value="options.use_speaker_boost"
        label="SPEAKER BOOST"
        @update:model-value="(v: boolean) => patch('use_speaker_boost', v)"
      />
    </div>

    <p class="opts__hint">
      Defaults equiparan la calidad por defecto de elevenlabs.io
      (stability 0.5 · similarity 0.85 · speaker boost on).
    </p>
  </aside>
</template>

<style scoped>
.opts {
  position: relative;
  width: 320px;
  background: var(--bg-1);
  border: 1px solid var(--line);
  border-radius: var(--radius-5);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  box-shadow: var(--shadow-card);
  transform: translateX(12px);
  opacity: 0;
  pointer-events: none;
  transition: transform var(--dur-slow) var(--ease-studio),
              opacity var(--dur-base) var(--ease-studio);
}
.opts--open { transform: translateX(0); opacity: 1; pointer-events: auto; }

.opts__head { display: flex; justify-content: space-between; align-items: center; }
.opts__close {
  width: 26px; height: 26px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent;
  border: 1px solid var(--line);
  border-radius: var(--radius-2);
  color: var(--fg-1);
  font-size: 16px; line-height: 1;
  cursor: pointer;
}
.opts__close:hover { color: var(--fg-0); border-color: var(--line-2); }

.opts__group { display: flex; flex-direction: column; gap: 6px; }
.opts__select { margin-top: 0; }
.opts__knobs { display: flex; gap: 16px; justify-content: space-between; }
.opts__group--switch { flex-direction: row; align-items: center; justify-content: space-between; }

.opts__hint {
  margin: 0;
  color: var(--fg-2);
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.5;
  letter-spacing: 0.02em;
}
</style>
