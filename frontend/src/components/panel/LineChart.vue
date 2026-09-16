<script setup lang="ts">
import { computed } from 'vue'

/*
 * A multi-series line chart with dashed grid lines and x labels. Missing
 * points (null) break the line instead of drawing a false zero.
 */
export interface ChartSeries {
  name: string
  color: string
  values: Array<number | null>
}

const props = withDefaults(defineProps<{ series: ChartSeries[]; labels: string[]; height?: number }>(), { height: 220 })

const W = 640
const PAD = 10

const top = computed(() => {
  let max = 0
  for (const s of props.series) for (const v of s.values) if (typeof v === 'number' && v > max) max = v
  if (max <= 0) return 4
  // A round top so the grid labels are readable.
  const magnitude = 10 ** Math.floor(Math.log10(max))
  const rounded = Math.ceil(max / magnitude) * magnitude
  return Math.max(4, rounded)
})

const plotHeight = computed(() => props.height - PAD * 2)
const y = (v: number) => PAD + plotHeight.value - (v / top.value) * plotHeight.value
const count = computed(() => Math.max(1, ...props.series.map((s) => s.values.length)))

const paths = computed(() =>
  props.series.map((s) => {
    const step = count.value > 1 ? W / (count.value - 1) : 0
    const segments: string[] = []
    let current: string[] = []
    s.values.forEach((v, i) => {
      if (typeof v === 'number') current.push(`${(i * step).toFixed(1)},${y(v).toFixed(1)}`)
      else if (current.length) {
        segments.push(current.join(' '))
        current = []
      }
    })
    if (current.length) segments.push(current.join(' '))
    // A single point still needs a visible mark.
    return { ...s, segments: segments.map((seg) => (seg.includes(' ') ? seg : `${seg} ${seg}`)) }
  }),
)

const grid = computed(() =>
  [0, 1, 2, 3, 4].map((i) => ({
    y: PAD + (plotHeight.value / 4) * i,
    label: new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 1 }).format(top.value - (top.value / 4) * i),
  })),
)

/** Up to six evenly spaced x labels. */
const xLabels = computed(() => {
  const n = props.labels.length
  if (n <= 6) return props.labels
  return [0, 1, 2, 3, 4, 5].map((i) => props.labels[Math.round((i * (n - 1)) / 5)] ?? '')
})
</script>

<template>
  <div class="chart">
    <div class="chart__plot">
      <div class="chart__y" :style="{ height: `${height}px` }">
        <span v-for="g in grid" :key="g.y" class="chart__ylabel num" :style="{ top: `${g.y}px` }">{{ g.label }}</span>
      </div>
      <svg width="100%" :height="height" :viewBox="`0 0 ${W} ${height}`" preserveAspectRatio="none" fill="none" aria-hidden="true">
        <line
          v-for="g in grid"
          :key="g.y"
          x1="0"
          :y1="g.y"
          :x2="W"
          :y2="g.y"
          stroke="var(--grid-line)"
          stroke-width="1"
          stroke-dasharray="4 4"
          vector-effect="non-scaling-stroke"
        />
        <template v-for="s in paths" :key="s.name">
          <polyline
            v-for="(seg, i) in s.segments"
            :key="i"
            :points="seg"
            :stroke="s.color"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            vector-effect="non-scaling-stroke"
          />
        </template>
      </svg>
    </div>
    <div class="chart__x">
      <span v-for="(l, i) in xLabels" :key="i" class="chart__xlabel num">{{ l }}</span>
    </div>
    <div v-if="series.length" class="chart__legend">
      <span v-for="s in series" :key="s.name" class="chart__legend-item">
        <span class="chart__swatch" :style="{ background: s.color }" />{{ s.name }}
      </span>
      <slot name="legend" />
    </div>
  </div>
</template>

<style scoped>
.chart__plot {
  display: flex;
  gap: 8px;
}
.chart__y {
  position: relative;
  width: 32px;
  flex: none;
}
.chart__ylabel {
  position: absolute;
  right: 0;
  transform: translateY(-50%);
  font-size: 11px;
  line-height: 14px;
  color: var(--text-meta);
  white-space: nowrap;
}
.chart svg {
  display: block;
  flex: 1;
  min-width: 0;
}
.chart__x {
  display: flex;
  justify-content: space-between;
  margin: 8px 0 0 40px;
}
.chart__xlabel {
  font-size: 12px;
  line-height: 16px;
  color: var(--text-meta);
}
.chart__legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-card);
}
.chart__legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  line-height: 16px;
  color: var(--text-secondary);
}
.chart__swatch {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
}
</style>
