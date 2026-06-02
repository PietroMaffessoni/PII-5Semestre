<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  items: {
    type: Array,
    default: () => [],
  },
  text: {
    type: String,
    default: '',
  },
})
</script>

<template>
  <article class="info-card">
    <h2>{{ title }}</h2>
    <p v-if="text">{{ text }}</p>
    <ul v-if="items.length">
      <li v-for="item in items" :key="item">{{ item }}</li>
    </ul>
  </article>
</template>

<style scoped>
.info-card {
  display: grid;
  gap: 0.9rem;
  padding: 1.4rem;
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  border-radius: 20px;
  box-shadow: var(--panel-shadow);
}

h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.12rem;
}

p,
li {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.55;
}

ul {
  display: grid;
  gap: 0.7rem;
  padding-left: 1.1rem;
  margin: 0;
}
</style>
