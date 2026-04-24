<template>
  <div class="app-shell">
    <router-view />
  </div>
</template>

<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background:
    radial-gradient(circle at top left, rgba(30, 136, 229, 0.2), transparent 24%),
    linear-gradient(180deg, #f5f7fb 0%, #e7edf5 100%);
  color: #10243a;
}

button,
input,
textarea {
  font: inherit;
}

a {
  color: inherit;
}

#app,
.app-shell {
  min-height: 100vh;
}
</style>
