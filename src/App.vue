<template>
  <div class="app-shell">
    <canvas v-if="!isNativeApp" id="particles-canvas"></canvas>
    <button type="button" class="theme-toggle" :aria-pressed="isDarkTheme" @click="toggleTheme">
      <span class="theme-toggle__icon" aria-hidden="true"></span>
      {{ isDarkTheme ? 'Claro' : 'Escuro' }}
    </button>
    <router-view />
  </div>
</template>

<style>
:root {
  --page-bg: linear-gradient(135deg, #fff8e0 0%, #d0dde9 100%);
  --text-primary: #10243a;
  --text-secondary: #4f647a;
  --panel-bg: rgba(255, 255, 255, 0.9);
  --panel-border: rgba(16, 36, 58, 0.08);
  --panel-shadow: 0 18px 50px rgba(16, 36, 58, 0.08);
  --surface-bg: #f8fbff;
  --surface-strong: #eaf2fb;
  --brand-gradient: linear-gradient(135deg, #e09144 0%, #5cb3a1 100%);
  --brand-soft: rgba(255, 255, 255, 0.08);
  --accent-primary: #5cb3a1;
  --chart-accent: #5cb3a1;
  --sql-bg: #f7d3a2;
  --sql-text: #24313a;
  --button-fill: #5cb3a1;
  --button-surface: linear-gradient(#5cb3a1, #5cb3a1);
  --button-text: #ffffff;
  --button-border: linear-gradient(#5cb3a1, #5cb3a1);
  --button-shadow: none;
  --secondary-button-fill: #edf3f9;
  --secondary-button-surface: linear-gradient(#edf3f9, #edf3f9);
  --secondary-button-text: #0f2742;
  --input-bg: #f8fbff;
  --input-border: rgba(35, 65, 95, 0.18);
  --particle-rgb: 255, 255, 255;
}

:root[data-theme='dark'] {
  --page-bg: linear-gradient(135deg, #02131a 0%, #12071e 100%);
  --text-primary: #f6fbff;
  --text-secondary: #c4d0dc;
  --panel-bg: rgba(35, 51, 65, 0.92);
  --panel-border: rgba(218, 235, 255, 0.16);
  --panel-shadow: 0 22px 70px rgba(0, 0, 0, 0.34);
  --surface-bg: rgba(25, 39, 52, 0.88);
  --surface-strong: rgba(44, 61, 78, 0.95);
  --brand-gradient: linear-gradient(135deg, #063946 0%, #281042 100%);
  --brand-soft: rgba(255, 255, 255, 0.11);
  --accent-primary: #cfd9ff;
  --chart-accent: #4b1c73;
  --sql-bg: #063946;
  --sql-text: #f6fbff;
  --button-fill: rgba(255, 255, 255, 0.08);
  --button-surface: linear-gradient(
    120deg,
    rgba(255, 255, 255, 0.32) 0%,
    rgba(255, 255, 255, 0.16) 24%,
    rgba(255, 255, 255, 0.02) 48%,
    rgba(0, 0, 0, 0.14) 68%,
    rgba(0, 0, 0, 0.08) 80%,
    rgba(255, 255, 255, 0.08) 100%
  );
  --button-text: #f8fbff;
  --button-border: linear-gradient(
    120deg,
    rgba(255, 255, 255, 0.78) 0%,
    rgba(255, 255, 255, 0.4) 22%,
    rgba(255, 255, 255, 0.08) 46%,
    rgba(0, 0, 0, 0.22) 72%,
    rgba(255, 255, 255, 0.34) 100%
  );
  --button-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.3),
    0 16px 34px rgba(0, 0, 0, 0.26);
  --secondary-button-fill: rgba(255, 255, 255, 0.07);
  --secondary-button-surface: linear-gradient(
    120deg,
    rgba(255, 255, 255, 0.26) 0%,
    rgba(255, 255, 255, 0.1) 26%,
    rgba(255, 255, 255, 0.02) 50%,
    rgba(0, 0, 0, 0.16) 68%,
    rgba(0, 0, 0, 0.09) 82%,
    rgba(255, 255, 255, 0.06) 100%
  );
  --secondary-button-text: #f6fbff;
  --input-bg: rgba(14, 27, 38, 0.78);
  --input-border: rgba(220, 235, 255, 0.18);
  --particle-rgb: 125, 158, 184;
}

* {
  box-sizing: border-box;
}

html {
  width: 100%;
  overflow-x: hidden;
}

body {
  margin: 0;
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--page-bg);
  background-attachment: fixed;
  background-size: cover;
  color: var(--text-primary);
  transition:
    background 220ms ease,
    color 220ms ease;
}

button,
input,
textarea {
  font: inherit;
  min-width: 0;
  max-width: 100%;
}

button {
  text-align: center;
  white-space: normal;
}

a {
  color: inherit;
}

#app,
.app-shell {
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
  overflow-y: auto;
}

.app-shell * {
  min-width: 0;
}

.app-shell main {
  width: 100%;
  max-width: 100%;
}

p,
h1,
h2,
h3,
li,
span,
strong,
small,
label,
button {
  overflow-wrap: anywhere;
}

#particles-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.app-shell > :not(canvas) {
  position: relative;
  z-index: 1;
}

.theme-toggle {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 5;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2.55rem;
  max-width: calc(100vw - 1.5rem);
  padding: 0.65rem 0.9rem;
  border: 1px solid transparent;
  border-radius: 999px;
  background:
    var(--secondary-button-surface) padding-box,
    var(--button-border) border-box;
  color: var(--secondary-button-text);
  box-shadow: var(--button-shadow);
  font-weight: 800;
  cursor: pointer;
  backdrop-filter: blur(18px) saturate(1.2);
}

.theme-toggle__icon {
  flex: 0 0 0.9rem;
  width: 0.9rem;
  height: 0.9rem;
  border-radius: 999px;
  background: currentColor;
  box-shadow: inset -0.28rem -0.16rem 0 rgba(255, 248, 224, 0.9);
}

:root[data-theme='dark'] .theme-toggle__icon {
  box-shadow: 0 0 0 0.2rem rgba(255, 255, 255, 0.12);
}

@media (max-width: 480px) {
  body {
    background-attachment: scroll;
  }

  .theme-toggle {
    top: 0.6rem;
    right: 0.6rem;
    min-height: 2.35rem;
    padding: 0.55rem 0.7rem;
    font-size: 0.9rem;
  }
}

@media (max-width: 360px) {
  .theme-toggle {
    gap: 0.35rem;
    padding: 0.5rem 0.62rem;
    font-size: 0.82rem;
  }
}
</style>

<script>
import { Capacitor } from '@capacitor/core';

export default {
  name: 'App',
  data() {
    return {
      theme: 'light',
      isNativeApp: Capacitor.isNativePlatform(),
      canvas: null,
      ctx: null,
      particles: [],
      mouseX: -1000,
      mouseY: -1000,
      animationFrameId: null,
    };
  },
  computed: {
    isDarkTheme() {
      return this.theme === 'dark';
    },
  },
  created() {
    const storedTheme = window.localStorage.getItem('theme');
    this.theme = storedTheme === 'dark' ? 'dark' : 'light';
    this.applyTheme();
  },
  mounted() {
    if (this.isNativeApp) {
      return;
    }

    this.setupCanvas();
    this.initializeParticles();
    this.animate();
    window.addEventListener('mousemove', this.handleMouseMove);
    window.addEventListener('mouseleave', this.handleMouseLeave);
    window.addEventListener('resize', this.handleResize);
  },
  beforeUnmount() {
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
    }

    window.removeEventListener('mousemove', this.handleMouseMove);
    window.removeEventListener('mouseleave', this.handleMouseLeave);
    window.removeEventListener('resize', this.handleResize);
  },
  methods: {
    applyTheme() {
      document.documentElement.dataset.theme = this.theme;
      window.localStorage.setItem('theme', this.theme);
      window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: this.theme } }));
    },
    toggleTheme() {
      this.theme = this.isDarkTheme ? 'light' : 'dark';
      this.applyTheme();
    },
    setupCanvas() {
      this.canvas = document.getElementById('particles-canvas');
      if (!this.canvas) {
        return;
      }

      this.ctx = this.canvas.getContext('2d');
      this.resizeCanvas();
    },
    resizeCanvas() {
      if (!this.canvas) {
        return;
      }

      this.canvas.width = window.innerWidth;
      this.canvas.height = window.innerHeight;
    },
    initializeParticles() {
      this.particles = [];
      const particleCount = 50;
      for (let i = 0; i < particleCount; i++) {
        this.particles.push({
          x: Math.random() * this.canvas.width,
          y: Math.random() * this.canvas.height,
          vx: (Math.random() - 0.5) * 0.5,
          vy: (Math.random() - 0.5) * 0.5,
          radius: Math.random() * 10 + 8,
          opacity: Math.random() * 0.5 + 0.3,
          targetOpacity: Math.random() * 0.5 + 0.3,
          baseOpacity: Math.random() * 0.5 + 0.3,
          opacityChangeTimer: Math.random() * 120 + 60,
          opacityChangeInterval: Math.random() * 120 + 60,
          vx_damping: 1,
          vy_damping: 1,
        });
      }
    },
    updateParticles() {
      const repulsionRadius = 120;
      const repulsionForce = 0.3;
      const opacityLerpSpeed = 0.02;
      const velocityDamping = 0.98;

      for (let particle of this.particles) {
        // Update opacity timer
        particle.opacityChangeTimer--;
        if (particle.opacityChangeTimer <= 0) {
          particle.targetOpacity = Math.random() * 0.5 + 0.3;
          particle.opacityChangeInterval = Math.random() * 120 + 60;
          particle.opacityChangeTimer = particle.opacityChangeInterval;
        }

        // Smoothly lerp opacity to target
        particle.opacity += (particle.targetOpacity - particle.opacity) * opacityLerpSpeed;

        // Calculate distance to mouse
        const dx = particle.x - this.mouseX;
        const dy = particle.y - this.mouseY;
        const distance = Math.sqrt(dx * dx + dy * dy);

        // Apply mouse repulsion
        if (distance < repulsionRadius && distance > 0) {
          const angle = Math.atan2(dy, dx);
          const force = (1 - distance / repulsionRadius) * repulsionForce;
          particle.vx += Math.cos(angle) * force;
          particle.vy += Math.sin(angle) * force;
          particle.targetOpacity *= 0.8; // Slightly reduce opacity when near mouse
        }

        // Apply damping
        particle.vx *= velocityDamping;
        particle.vy *= velocityDamping;

        // Update position
        particle.x += particle.vx;
        particle.y += particle.vy;

        // Wrap around edges
        if (particle.x < 0) particle.x = this.canvas.width;
        if (particle.x > this.canvas.width) particle.x = 0;
        if (particle.y < 0) particle.y = this.canvas.height;
        if (particle.y > this.canvas.height) particle.y = 0;
      }
    },
    drawParticles() {
      // Clear canvas
      this.ctx.fillStyle = 'rgba(255, 255, 255, 0)';
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

      // Draw particles
      const particleColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--particle-rgb')
        .trim();
      for (let particle of this.particles) {
        this.ctx.fillStyle = `rgba(${particleColor}, ${particle.opacity})`;
        this.ctx.beginPath();
        this.ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
        this.ctx.fill();
      }
    },
    animate() {
      this.updateParticles();
      this.drawParticles();
      this.animationFrameId = requestAnimationFrame(this.animate);
    },
    handleMouseMove(event) {
      this.mouseX = event.clientX;
      this.mouseY = event.clientY;
    },
    handleMouseLeave() {
      this.mouseX = -1000;
      this.mouseY = -1000;
    },
    handleResize() {
      this.resizeCanvas();
      // Recalculate particle positions to fit new canvas
      for (let particle of this.particles) {
        particle.x = Math.min(particle.x, this.canvas.width);
        particle.y = Math.min(particle.y, this.canvas.height);
      }
    },
  },
};
</script>
