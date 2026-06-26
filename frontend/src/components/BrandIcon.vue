<script setup lang="ts">
withDefaults(
  defineProps<{
    /** 渲染尺寸（px） */
    size?: number
  }>(),
  { size: 40 },
)
</script>

<template>
  <!-- 浪潮品牌标：圆角方块 + 双波浪 path，不依赖字体渲染 -->
  <svg
    class="brand-icon"
    :width="size"
    :height="size"
    viewBox="0 0 40 40"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <rect width="40" height="40" rx="10" fill="#0066CC" />
    <path
      d="M8 18 C12 14, 16 22, 20 18 S28 14, 32 18"
      stroke="#ffffff"
      stroke-width="2.5"
      stroke-linecap="round"
      fill="none"
    />
    <path
      d="M8 26 C12 22, 16 30, 20 26 S28 22, 32 26"
      stroke="#ffffff"
      stroke-width="2.5"
      stroke-linecap="round"
      fill="none"
      opacity="0.85"
    />
  </svg>
</template>

<style scoped>
.brand-icon {
  display: block;
  flex-shrink: 0;
}
</style>
