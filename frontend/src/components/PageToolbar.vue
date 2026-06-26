<script setup lang="ts">
defineProps<{
  title?: string
}>()
</script>

<template>
  <div class="page-toolbar">
    <h2 v-if="title">{{ title }}</h2>
    <div class="page-toolbar-actions">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.page-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
