<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'
import Icon from '@/components/Icon.vue'
import PageTabs from '@/components/panel/PageTabs.vue'
import ClassCard, { type ClassRow } from '@/components/panel/ClassCard.vue'
import CategoryBars, { type BarDatum } from '@/components/panel/CategoryBars.vue'
import CategoryChip from '@/components/panel/CategoryChip.vue'
import StatusPill from '@/components/panel/StatusPill.vue'
import WhyDialog from '@/components/panel/WhyDialog.vue'
import EmptyState from '@/components/panel/EmptyState.vue'
import { copy } from '@/copy'
import { fetchItems, fetchOverview, type Overview, type PanelItem, type RangeName } from '@/api/panel'
import { categoryMeta, familyMeta, codesOfFamily, CONTENT_FAMILIES, BINARY_OFFENSIVE, firedCategories } from '@/lib/categories'
import { STATUS_ORDER, statusMeta, type ModerationTone } from '@/lib/moderation'
import { formatAgo, formatChange, formatCount, formatPercent, initials } from '@/lib/format'
import { usePoll } from '@/composables/usePoll'

/*
 * S1 Genel Bakış. Top to bottom: how much the system analysed, what is
 * waiting for a person, how the detections split across the moderation
 * classes, and the last messages with the classification each one got.
 *
 * Every number on this page is counted by the server (/api/panel/overview);
 * the screen groups and formats them and decides nothing.
 */
const range = ref<RangeName>('today')
const overview = shallowRef<Overview | null>(null)
const recent = shallowRef<PanelItem[]>([])
const detectedOnly = ref(true)
const failed = ref(false)
const now = ref(Date.now())
const explaining = shallowRef<PanelItem | null>(null)

const tabs = computed(() => (['live', 'today', 'week'] as const).map((key) => ({ key, label: copy.panel.ranges[key]! })))

async function load() {
  const requested = range.value
  const wantDetected = detectedOnly.value
  const [o, r] = await Promise.all([fetchOverview(requested), fetchItems({ detected: wantDetected, limit: 8 })])
  now.value = Date.now()
  if (requested !== range.value || wantDetected !== detectedOnly.value) return
  failed.value = !o.ok
  if (o.ok) overview.value = o.data
  if (r.ok) recent.value = r.data.items
}
const poll = usePoll(load, 5000)
watch(range, () => {
  overview.value = null
  void poll.refresh()
})
watch(detectedOnly, () => {
  recent.value = []
  void poll.refresh()
})

// ---------------------------------------------------------------- headline

const windowText = computed(() => copy.overview.totalWindow[range.value] ?? '')

/** The general offensive signal is its own card row, not a content family. */
const offensiveTotal = computed(() => {
  for (const c of overview.value?.categories ?? []) if (c.code === BINARY_OFFENSIVE) return c.total
  return null
})

const headlineStats = computed(() => {
  const o = overview.value
  if (!o) return []
  return [
    {
      key: 'detected',
      icon: 'alert' as const,
      label: copy.overview.detectedLabel,
      value: formatCount(o.detected.value),
      sub: formatPercent(o.detected.share_pct),
    },
    {
      key: 'automatic',
      icon: 'bolt' as const,
      label: copy.overview.automaticLabel,
      value: formatCount(o.automatic.value),
      sub: null,
    },
    {
      key: 'offensive',
      icon: 'brain' as const,
      label: copy.overview.offensiveLabel,
      value: formatCount(offensiveTotal.value),
      sub: null,
    },
    {
      key: 'handled',
      icon: 'check' as const,
      label: copy.overview.handledLabel,
      value: formatCount(o.queue.reviewed),
      sub: null,
    },
  ]
})

const analysedChange = computed(() => formatChange(overview.value?.analysed.change_pct))
const analysedUp = computed(() => (overview.value?.analysed.change_pct ?? 0) > 0)

// ------------------------------------------------------------ class cards

/**
 * One card per content-code family, in code order, with every category the
 * CONTRACT defines inside it - not only the ones the AI produces today.
 *
 * The server counts a category only while the inference service reports it in
 * /health (AI/serving/capabilities.py); a code it does not report gets no row
 * of its own. Dropping those codes hid two whole classes (C örtük saldırganlık
 * and D aşağılayıcı ironi) and read as if the panel only knew about two. They
 * are shown with a null total, which ClassCard renders as "henüz üretilmiyor"
 * rather than as a zero, so the card states the difference between "looked for,
 * found none" and "not measured".
 *
 * When the server reports no content category at all the AI is unreachable or
 * misconfigured, and "not produced yet" would be the wrong word for it: the
 * page falls back to the error line instead.
 */
const classes = computed(() => {
  const counted = new Map<string, number>()
  for (const c of overview.value?.categories ?? []) {
    if (c.code !== BINARY_OFFENSIVE) counted.set(c.code, c.total)
  }
  if (counted.size === 0) return []
  return CONTENT_FAMILIES.map((family) => {
    const meta = familyMeta(family)
    const rows: ClassRow[] = codesOfFamily(family).map((code) => ({
      code,
      label: categoryMeta(code).label,
      total: counted.get(code) ?? null,
    }))
    return { family, title: meta.label, icon: meta.icon, color: meta.color, ink: meta.ink, tint: meta.tint, rows }
  })
})

// ----------------------------------------------------------- distribution

const bars = computed<BarDatum[]>(() => {
  const out: BarDatum[] = []
  for (const c of overview.value?.categories ?? []) {
    // The general offensive signal fires beside a content code rather than
    // instead of one, so it belongs in the headline, not in this comparison.
    if (c.total === 0 || c.code === BINARY_OFFENSIVE) continue
    const meta = categoryMeta(c.code)
    out.push({ code: c.code, label: meta.label, value: c.total, color: meta.color, ink: meta.ink })
  }
  out.sort((a, b) => b.value - a.value)
  return out
})

/**
 * How many the system handed to a person IN THE SELECTED WINDOW. The queue
 * counts are a running backlog with no time filter, so they must never be the
 * headline of a window-scoped page; the backlog is the line underneath.
 */
const humanReview = computed(() => {
  const o = overview.value
  if (!o) return null
  const value = o.verdicts.review + o.verdicts.escalate
  return {
    value,
    share: o.detected.value > 0 ? (value / o.detected.value) * 100 : null,
    waiting: o.queue.pending_detected,
  }
})

// --------------------------------------------------------- status summary

/** The verdict counts the server sent, as the four words the dashboard uses. */
const statuses = computed(() => {
  const v = overview.value?.verdicts
  if (!v) return []
  const counts: Record<ModerationTone, number> = {
    clean: v.clean,
    warning: v.nudge,
    review: v.review + v.escalate,
    blocked: v.block,
    incomplete: v.undecided,
  }
  let total = 0
  for (const tone of STATUS_ORDER) total += counts[tone]
  return STATUS_ORDER.filter((tone) => counts[tone] > 0).map((tone) => ({
    tone,
    meta: statusMeta(tone),
    value: counts[tone],
    share: total > 0 ? (counts[tone] / total) * 100 : 0,
  }))
})

// ----------------------------------------------------------------- recent

/**
 * What the row is labelled with: the content codes that fired. When none did,
 * the general offensive signal is the only thing there is to show, so it takes
 * the column on its own.
 */
function categoriesOf(item: PanelItem) {
  const fired = firedCategories(item.result)
  const content = fired.filter((f) => f.code !== BINARY_OFFENSIVE)
  return content.length > 0 ? content : fired
}

function preview(text: string): string {
  return text.length > 96 ? `${text.slice(0, 96)}…` : text
}
</script>

<template>
  <PageTabs v-model="range" :tabs="tabs" />

  <div class="stack">
    <p v-if="failed && !overview" class="muted">{{ copy.panel.loadFailed }}</p>

    <!-- 1. how much was analysed, and what is waiting for a person -->
    <div class="headline">
      <section class="card hero">
        <div class="hero__label">
          <Icon name="message" :size="16" :stroke="1.8" />
          <span>{{ copy.overview.totalLabel }}</span>
        </div>
        <div class="hero__row">
          <span class="hero__value num">{{ formatCount(overview?.analysed.value) ?? '—' }}</span>
          <span v-if="analysedChange" class="chip hero__change" :class="{ 'hero__change--up': analysedUp }">
            {{ analysedChange }}
          </span>
        </div>
        <p class="hero__sub">{{ copy.overview.totalUnit }} · {{ windowText }}</p>

        <dl class="hero__stats">
          <div v-for="stat in headlineStats" :key="stat.key" class="stat">
            <dt class="stat__label"><Icon :name="stat.icon" :size="15" :stroke="1.8" />{{ stat.label }}</dt>
            <dd class="stat__value">
              <span v-if="stat.value !== null" class="num">{{ stat.value }}</span>
              <span v-else class="unavailable">—</span>
              <span v-if="stat.sub" class="meta stat__sub">{{ stat.sub }}</span>
            </dd>
          </div>
        </dl>
      </section>

      <RouterLink :to="{ name: 'queue' }" class="card review">
        <div class="review__label">
          <Icon name="flag" :size="16" :stroke="1.8" />
          <span>{{ copy.overview.humanReview }}</span>
        </div>
        <div class="review__row">
          <span class="review__value num">{{ formatCount(humanReview?.value) ?? '—' }}</span>
          <span v-if="humanReview?.share != null" class="chip review__share">
            {{ copy.overview.humanReviewShare(formatPercent(humanReview.share)!) }}
          </span>
        </div>
        <p class="review__note">{{ copy.overview.humanReviewNote }}</p>
        <div class="review__foot">
          <span class="meta">{{ copy.overview.humanReviewTotal(formatCount(humanReview?.waiting) ?? '—') }}</span>
          <span class="review__cta">{{ copy.overview.humanReviewCta }}<Icon name="arrowRight" :size="16" :stroke="1.8" /></span>
        </div>
      </RouterLink>
    </div>

    <!-- 2. one card per moderation class, every category counted -->
    <section>
      <div class="section-head">
        <h2 class="section-title">{{ copy.overview.classes }}</h2>
        <span class="muted">{{ copy.overview.classesNote }}</span>
      </div>
      <div v-if="classes.length" class="classes">
        <ClassCard
          v-for="c in classes"
          :key="c.family"
          :title="c.title"
          :icon="c.icon"
          :color="c.color"
          :ink="c.ink"
          :tint="c.tint"
          :rows="c.rows"
        />
      </div>
      <p v-else-if="overview" class="muted">{{ overview.categories_error ?? copy.panel.enginesEmpty }}</p>
    </section>

    <!-- 3. distribution and the four moderation outcomes -->
    <div class="split">
      <div class="card">
        <div class="card__head">
          <h3 class="card__title">{{ copy.overview.distribution }}</h3>
          <span class="muted">{{ copy.panel.rangeWindow[range] }}</span>
        </div>
        <CategoryBars v-if="bars.length" :data="bars" />
        <p v-else-if="overview" class="muted distribution__empty">{{ copy.overview.distributionEmpty }}</p>
      </div>

      <div class="card">
        <h3 class="card__title">{{ copy.overview.statusTitle }}</h3>
        <p class="meta status__note">{{ copy.overview.statusNote }}</p>
        <div v-if="statuses.length" class="status__bar">
          <span
            v-for="s in statuses"
            :key="s.tone"
            class="status__segment"
            :style="{ width: `${s.share}%`, background: s.meta.ink }"
            :title="s.meta.label"
          />
        </div>
        <ul class="status__list">
          <li v-for="s in statuses" :key="s.tone" class="status__item">
            <span class="status__dot" :style="{ background: s.meta.ink }" />
            <span class="status__name">{{ s.meta.label }}</span>
            <span class="num status__count">{{ formatCount(s.value) }}</span>
            <span class="num status__share">{{ formatPercent(s.share) }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- 4. the last messages and what each one was classified as -->
    <div class="card">
      <div class="card__head activity__head">
        <h3 class="card__title">{{ copy.overview.recent }}</h3>
        <div class="activity__controls">
          <div class="toggle" role="group">
            <button
              type="button"
              class="toggle__btn"
              :class="{ 'toggle__btn--on': detectedOnly }"
              @click="detectedOnly = true"
            >
              {{ copy.overview.recentFilter.detected }}
            </button>
            <button
              type="button"
              class="toggle__btn"
              :class="{ 'toggle__btn--on': !detectedOnly }"
              @click="detectedOnly = false"
            >
              {{ copy.overview.recentFilter.all }}
            </button>
          </div>
          <RouterLink :to="{ name: 'queue' }" class="btn btn--ghost">
            {{ copy.panel.goQueue }}
            <Icon name="arrowRight" :size="16" :stroke="1.8" />
          </RouterLink>
        </div>
      </div>

      <table v-if="recent.length" class="activity">
        <thead>
          <tr>
            <th class="activity__content">{{ copy.overview.columns.content }}</th>
            <th>{{ copy.overview.columns.user }}</th>
            <th>{{ copy.overview.columns.category }}</th>
            <th>{{ copy.overview.columns.status }}</th>
            <th class="activity__time">{{ copy.overview.columns.time }}</th>
            <th><span class="sr-only">{{ copy.overview.why }}</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in recent" :key="item.id">
            <td class="activity__content">{{ preview(item.text) }}</td>
            <td class="activity__user">
              <span class="who">
                <span class="who__avatar">{{ initials(item.nickname) }}</span>
                <span class="who__name">{{ item.nickname }}</span>
              </span>
            </td>
            <td class="activity__cats">
              <span class="cats">
                <CategoryChip v-for="f in categoriesOf(item)" :key="f.code" :code="f.code" />
                <span v-if="categoriesOf(item).length === 0" class="chip">{{ copy.panel.noDetection }}</span>
              </span>
            </td>
            <td class="activity__status"><StatusPill :action="item.final_action" /></td>
            <td class="activity__time meta">{{ formatAgo(item.created_at, now) }}</td>
            <td class="activity__why">
              <button type="button" class="btn btn--secondary why" @click="explaining = item">
                <Icon name="info" :size="15" :stroke="1.8" />
                {{ copy.overview.why }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <EmptyState v-else-if="overview" icon="check" :title="copy.overview.recentEmpty" class="activity__empty" />
    </div>
  </div>

  <WhyDialog v-if="explaining" :item="explaining" @close="explaining = null" />
</template>

<style scoped>
/* 1 -------------------------------------------------------------- headline */
.headline {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  gap: 20px;
  align-items: stretch;
}
.hero {
  display: flex;
  flex-direction: column;
}
.hero__label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-muted);
}
.hero__row {
  margin-top: 8px;
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}
.hero__value {
  font-size: 52px;
  line-height: 60px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-heading);
}
.hero__change--up {
  background: var(--cat-clean-bg);
  color: var(--mint);
}
.hero__sub {
  margin: 4px 0 0;
  font-size: 14px;
  color: var(--text-meta);
}
.hero__stats {
  margin: 20px 0 0;
  padding-top: 18px;
  border-top: 1px solid var(--border-card);
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  flex: 1;
  align-content: end;
}
.stat__label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  line-height: 16px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.stat__value {
  margin: 6px 0 0;
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 22px;
  line-height: 28px;
  font-weight: 700;
  color: var(--text-heading);
}
.stat__sub {
  font-size: 13px;
  font-weight: 500;
}
.unavailable {
  color: var(--text-meta);
}

.review {
  display: flex;
  flex-direction: column;
  color: inherit;
  border-color: var(--accent);
  background: linear-gradient(180deg, var(--bg-subtle) 0%, var(--bg-raised) 68%);
  transition: border-color 0.15s;
}
.review:hover {
  color: inherit;
  border-color: var(--accent-hover);
}
.review__label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--accent);
}
.review__row {
  margin-top: 8px;
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}
.review__share {
  background: var(--bg-subtle);
  color: var(--text-secondary);
}
.review__value {
  font-size: 52px;
  line-height: 60px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-heading);
}
.review__note {
  margin: 4px 0 0;
  font-size: 13px;
  line-height: 19px;
  color: var(--text-secondary);
}
.review__foot {
  margin-top: auto;
  padding-top: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}
.review__cta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--accent);
}

/* 2 ---------------------------------------------------------- class cards */
.section-head {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.classes {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
  align-items: stretch;
}

/* 3 -------------------------------------------------- distribution, status */
.split {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}
.distribution__empty {
  margin-top: 20px;
}
.status__note {
  margin: 6px 0 0;
}
.status__bar {
  margin-top: 16px;
  display: flex;
  height: 10px;
  border-radius: var(--radius-full);
  overflow: hidden;
  background: var(--bg-subtle);
  gap: 2px;
}
.status__segment {
  display: block;
  height: 100%;
}
.status__list {
  list-style: none;
  margin: 14px 0 0;
  padding: 0;
}
.status__item {
  display: grid;
  grid-template-columns: 10px 1fr auto 56px;
  align-items: center;
  gap: 10px;
  height: 38px;
  border-bottom: 1px solid var(--border-divider);
}
.status__item:last-child {
  border-bottom: 0;
}
.status__dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
}
.status__name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}
.status__count {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-heading);
}
.status__share {
  font-size: 13px;
  color: var(--text-meta);
  text-align: right;
}

/* 4 -------------------------------------------------------------- activity */
.activity__head {
  align-items: center;
  margin-bottom: 4px;
}
.activity__controls {
  display: flex;
  align-items: center;
  gap: 16px;
}
.toggle {
  display: inline-flex;
  padding: 2px;
  gap: 2px;
  background: var(--bg-subtle);
  border-radius: var(--radius-full);
}
.toggle__btn {
  height: 28px;
  padding: 0 14px;
  border: 0;
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.toggle__btn--on {
  background: var(--bg-raised);
  color: var(--text-heading);
}

.activity {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
}
.activity th {
  text-align: left;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-meta);
  padding: 10px 12px 10px 0;
  border-bottom: 1px solid var(--border-divider);
  white-space: nowrap;
}
.activity td {
  padding: 12px 12px 12px 0;
  border-bottom: 1px solid var(--border-divider);
  font-size: 14px;
  vertical-align: middle;
}
.activity tbody tr:last-child td {
  border-bottom: 0;
}
.activity tbody tr:hover td {
  background: var(--bg-subtle);
}
.activity__content {
  width: 42%;
  color: var(--text-primary);
}
.activity__time {
  white-space: nowrap;
}
.who {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}
.who__avatar {
  width: 28px;
  height: 28px;
  flex: none;
  border-radius: var(--radius-full);
  background: var(--bg-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}
.who__name {
  font-size: 13px;
  color: var(--text-secondary);
}
.cats {
  display: inline-flex;
  gap: 6px;
  flex-wrap: wrap;
}
.why {
  height: 28px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 500;
}
.activity__empty {
  border: 0;
  padding: 40px 0 8px;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

/* ------------------------------------------------------------- narrow */
@media (max-width: 1279px) {
  .headline,
  .split {
    grid-template-columns: 1fr;
  }
  .classes {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .hero__value,
  .review__value {
    font-size: 42px;
    line-height: 50px;
  }
}

/* -------------------------------------------------------------- phone */
/*
 * One column, and the six-column activity table becomes one card per
 * message: the text and its categories get the full width, and who / what /
 * when sit on one line underneath.
 */
@media (max-width: 599px) {
  .headline,
  .split,
  .classes {
    grid-template-columns: 1fr;
    gap: 14px;
  }
  .hero__value,
  .review__value {
    font-size: 38px;
    line-height: 46px;
  }
  .hero__stats {
    margin-top: 16px;
    padding-top: 14px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px 12px;
  }
  /* Two columns is room enough to wrap: "Genel saldırganlık sinyali" must
     not lose its last word to an ellipsis. */
  .stat__label {
    white-space: normal;
    align-items: flex-start;
  }
  .stat__value {
    font-size: 20px;
    line-height: 26px;
  }
  .section-head {
    gap: 4px;
    margin-bottom: 10px;
  }
  .review__foot {
    padding-top: 12px;
  }

  .activity,
  .activity tbody,
  .activity tr {
    display: block;
    width: 100%;
  }
  .activity thead {
    display: none;
  }
  .activity tbody tr {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 10px;
    padding: 14px 0;
    border-bottom: 1px solid var(--border-divider);
  }
  .activity tbody tr:last-child {
    border-bottom: 0;
    padding-bottom: 0;
  }
  .activity tbody tr:hover td {
    background: transparent;
  }
  /* No width here: the per-cell rules below would lose to it on specificity. */
  .activity td {
    display: block;
    padding: 0;
    border: 0;
  }
  .activity__content {
    order: 1;
    width: 100%;
    font-size: 15px;
    line-height: 22px;
  }
  .activity__cats {
    order: 2;
    width: 100%;
  }
  /* Who, what and when share one line under the message and its categories. */
  .activity__user {
    order: 3;
  }
  .activity__status {
    order: 4;
  }
  .activity__time {
    order: 5;
    margin-left: auto;
  }
  .activity__why {
    order: 6;
    width: 100%;
  }
  .why {
    width: 100%;
    height: 36px;
  }

  .activity__head {
    flex-wrap: wrap;
  }
  .activity__controls {
    width: 100%;
    justify-content: space-between;
    gap: 10px;
  }
  .toggle {
    flex: 1;
  }
  .toggle__btn {
    flex: 1;
    height: 34px;
  }

  .status__item {
    grid-template-columns: 10px 1fr auto 48px;
    height: 42px;
  }
}
</style>
