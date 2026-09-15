<script setup lang="ts">
/*
 * design-system 4.1. The only button in the application; a second button
 * implementation anywhere is a defect (9.1). Text only, sentence case, no
 * icons, no arrows, no spinner. Loading is shown by the caller changing the
 * label to its progressive form and setting disabled.
 */
withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost'
    size?: 'md' | 'sm'
    disabled?: boolean
    type?: 'button' | 'submit'
  }>(),
  { variant: 'secondary', size: 'md', disabled: false, type: 'button' },
)
defineEmits<{ click: [event: MouseEvent] }>()
</script>

<template>
  <v-btn
    :class="['base-button', `base-button--${variant}`, `base-button--${size}`]"
    :disabled="disabled"
    :type="type"
    :ripple="false"
    variant="flat"
    @click="$emit('click', $event)"
  >
    <slot />
  </v-btn>
</template>

<style scoped>
.base-button {
  min-width: 0;
  border-radius: var(--radius-control);
  font-family: var(--font-family-sans);
  font-weight: 500;
  letter-spacing: 0;
  text-transform: none;
  box-shadow: none;
  transition:
    background-color var(--motion-fast),
    color var(--motion-fast);
}
/* Vuetify's hover/press overlays are replaced by the states below. */
.base-button :deep(.v-btn__overlay),
.base-button :deep(.v-btn__underlay) {
  display: none;
}

.base-button--md {
  height: 36px;
  padding: 0 16px;
  font-size: 14px;
}
.base-button--sm {
  height: 28px;
  padding: 0 12px;
  font-size: 13px;
}

.base-button--primary {
  background: var(--accent);
  color: var(--text-on-accent);
  border: none;
}
.base-button--primary:hover {
  background: var(--accent-hover);
}
.base-button--primary:active {
  background: var(--accent-pressed);
}

.base-button--secondary {
  background: transparent;
  color: var(--text-body);
  border: 1px solid var(--border-default);
}
.base-button--secondary:hover {
  background: var(--surface-hover);
}

.base-button--ghost {
  background: transparent;
  color: var(--text-muted);
  border: none;
}
.base-button--ghost:hover {
  color: var(--text-body);
}

/* Disabled: 50% opacity, not-allowed, no hover response. */
.base-button.v-btn--disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: auto;
}
.base-button--primary.v-btn--disabled,
.base-button--primary.v-btn--disabled:hover {
  background: var(--accent);
  color: var(--text-on-accent);
}
.base-button--secondary.v-btn--disabled:hover {
  background: transparent;
}
.base-button--ghost.v-btn--disabled:hover {
  color: var(--text-muted);
}

.base-button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
</style>
