<template>
  <div class="app-shell">
    <canvas id="particles-canvas"></canvas>
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
  background: linear-gradient(135deg, #FFF8E0 0%, #D0DDE9 100%);
  background-attachment: fixed;
  background-size: cover;
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
  position: relative;
  overflow: hidden;
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
</style>

<script>
export default {
  name: 'App',
  data() {
    return {
      canvas: null,
      ctx: null,
      particles: [],
      mouseX: -1000,
      mouseY: -1000,
      animationFrameId: null,
    };
  },
  mounted() {
    this.setupCanvas();
    this.initializeParticles();
    this.animate();
    window.addEventListener('mousemove', this.handleMouseMove);
    window.addEventListener('mouseleave', this.handleMouseLeave);
    window.addEventListener('resize', this.handleResize);
  },
  beforeUnmount() {
    cancelAnimationFrame(this.animationFrameId);
    window.removeEventListener('mousemove', this.handleMouseMove);
    window.removeEventListener('mouseleave', this.handleMouseLeave);
    window.removeEventListener('resize', this.handleResize);
  },
  methods: {
    setupCanvas() {
      this.canvas = document.getElementById('particles-canvas');
      this.ctx = this.canvas.getContext('2d');
      this.resizeCanvas();
    },
    resizeCanvas() {
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
      for (let particle of this.particles) {
        this.ctx.fillStyle = `rgba(255, 255, 255, ${particle.opacity})`;
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
