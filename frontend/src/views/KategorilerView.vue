<script setup lang="ts">
import StatusWord from '@/components/ui/StatusWord.vue'
import { CONTENT_CODES, FAMILIES, contentLabel, familyLabel, familyOf } from '@/contract/labels'
import { copy } from '@/copy'

/*
 * pages-spec 3: a static reference of the sixteen content categories,
 * grouped by family with a plain heading above each group. No scores.
 *
 * Agreed for this build: code and Turkish label come from the contract
 * (codes.py); definition, threshold, action and module status render as
 * "veri yok" until the API serves them. No value is invented, and the
 * placeholder numbers in thresholds.yaml are not copied onto the screen.
 */
const groups = FAMILIES.map((family) => ({
  family,
  codes: CONTENT_CODES.filter((code) => familyOf(code) === family),
}))
</script>

<template>
  <div class="kategoriler">
    <h1 class="kategoriler__title">{{ copy.kategoriler.title }}</h1>

    <section v-for="group in groups" :key="group.family" class="kategoriler__group">
      <h2 class="kategoriler__family">{{ familyLabel(group.family) }}</h2>
      <v-table class="kategoriler__table">
        <!-- Same column widths in every family table, so the groups line up. -->
        <colgroup>
          <col style="width: 8%" />
          <col style="width: 28%" />
          <col style="width: 24%" />
          <col style="width: 12%" />
          <col style="width: 12%" />
          <col style="width: 16%" />
        </colgroup>
        <thead>
          <tr>
            <th scope="col">{{ copy.kategoriler.columns.code }}</th>
            <th scope="col">{{ copy.kategoriler.columns.label }}</th>
            <th scope="col">{{ copy.kategoriler.columns.definition }}</th>
            <th scope="col" class="num">{{ copy.kategoriler.columns.threshold }}</th>
            <th scope="col">{{ copy.kategoriler.columns.action }}</th>
            <th scope="col">{{ copy.kategoriler.columns.module }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="code in group.codes" :key="code">
            <td class="code">{{ code }}</td>
            <td>{{ contentLabel(code) }}</td>
            <td><StatusWord status="noData" /></td>
            <td class="num"><StatusWord status="noData" /></td>
            <td><StatusWord status="noData" /></td>
            <td><StatusWord status="noData" /></td>
          </tr>
        </tbody>
      </v-table>
    </section>
  </div>
</template>

<style scoped>
.kategoriler__title {
  margin: 0 0 24px;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--text-primary);
}
.kategoriler__group + .kategoriler__group {
  margin-top: 48px;
}
.kategoriler__family {
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--text-primary);
}

/* design-system 4.15 */
.kategoriler__table {
  background: transparent;
  color: var(--text-body);
  border-radius: 0;
}
.kategoriler__table :deep(table) {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
}
.kategoriler__table :deep(thead th) {
  position: sticky;
  top: 0;
  height: 40px;
  padding: 0 16px 0 0;
  background: var(--surface-page);
  border-bottom: 1px solid var(--border-default);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  text-align: left;
}
.kategoriler__table :deep(tbody td) {
  height: 44px;
  padding: 0 16px 0 0;
  border-bottom: 1px solid var(--border-divider);
  font-size: 14px;
  color: var(--text-body);
}
.kategoriler__table :deep(tbody tr:hover > td) {
  background: transparent;
}
.kategoriler__table :deep(.num) {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
/* A right-aligned column followed by a left-aligned one needs its own gap. */
.kategoriler__table :deep(.num + th),
.kategoriler__table :deep(.num + td) {
  padding-left: 24px;
}
.kategoriler__table :deep(.code) {
  color: var(--text-primary);
  font-weight: 500;
}
</style>
