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
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(7, 34, 66, 0.12);
  border-radius: 20px;
  box-shadow: 0 18px 40px rgba(7, 34, 66, 0.08);
}

h2 {
  margin: 0;
  color: #0f2742;
  font-size: 1.12rem;
}

p,
li {
  margin: 0;
  color: #35506d;
  line-height: 1.55;
}

ul {
  display: grid;
  gap: 0.7rem;
  padding-left: 1.1rem;
  margin: 0;
}
</style>
