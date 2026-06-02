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
  background: #ffffff;
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
