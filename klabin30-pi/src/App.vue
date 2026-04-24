<script setup>
import InfoCard from './components/InfoCard.vue'
import { projectCards } from './data/projectContent'

const highlights = [
  'Pergunta de negocio em linguagem natural',
  'Recuperacao semantica de tabelas e campos SAP',
  'Geracao assistida de scripts de extracao',
]
</script>

<template>
  <main class="page-shell">
    <section class="hero">
      <div class="hero-copy">
        <span class="eyebrow">TI | Sponsor: Abdul Latif | Fluxo: Record to Report</span>
        <h1>30 - Criacao automatizada de scripts para visualizacao de dados</h1>
        <p>
          Um assistente para traduzir perguntas de negocio em recomendacoes tecnicas de dados SAP,
          acelerando a construcao de dashboards e reduzindo o retrabalho entre negocio e TI.
        </p>
        <ul class="highlight-list">
          <li v-for="item in highlights" :key="item">{{ item }}</li>
        </ul>
      </div>

      <aside class="hero-panel">
        <div class="badge-box">
          <span>Tamanho da acao</span>
          <strong>M</strong>
        </div>
        <div class="brand-box">
          <span>Klabin</span>
          <small>Scaffold inicial do projeto</small>
        </div>
      </aside>
    </section>

    <section class="grid">
      <InfoCard :title="projectCards.problema.title" :text="projectCards.problema.text" />
      <InfoCard :title="projectCards.estrategia.title" :items="projectCards.estrategia.items" />
      <InfoCard :title="projectCards.valor.title" :items="projectCards.valor.items" />
      <InfoCard :title="projectCards.impacto.title" :items="projectCards.impacto.items" />
      <InfoCard :title="projectCards.riscos.title" :items="projectCards.riscos.items" />
      <InfoCard :title="projectCards.publico.title" :items="projectCards.publico.items" />
      <InfoCard :title="projectCards.sinergia.title" :text="projectCards.sinergia.text" />
    </section>
  </main>
</template>

<style scoped>
:global(*) {
  box-sizing: border-box;
}

:global(body) {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background:
    radial-gradient(circle at top left, rgba(252, 214, 92, 0.45), transparent 28%),
    linear-gradient(180deg, #f6f8fb 0%, #e8eef5 100%);
  color: #10243a;
}

:global(a) {
  color: inherit;
}

.page-shell {
  max-width: 1240px;
  margin: 0 auto;
  padding: 2rem 1.25rem 3rem;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(280px, 0.8fr);
  gap: 1.25rem;
  margin-bottom: 1.25rem;
}

.hero-copy,
.hero-panel {
  border-radius: 28px;
  padding: 1.7rem;
  box-shadow: 0 20px 60px rgba(15, 39, 66, 0.1);
}

.hero-copy {
  background: linear-gradient(135deg, #0f2742 0%, #1a4c7d 100%);
  color: #f7fafc;
}

.hero-panel {
  display: grid;
  gap: 1rem;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(10px);
}

.eyebrow {
  display: inline-block;
  margin-bottom: 1rem;
  color: #d7e6f5;
  font-size: 0.88rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: clamp(2rem, 4vw, 3.4rem);
  line-height: 1.02;
}

.hero-copy p {
  max-width: 54rem;
  margin: 1rem 0 0;
  color: rgba(247, 250, 252, 0.86);
  font-size: 1.02rem;
  line-height: 1.7;
}

.highlight-list {
  display: grid;
  gap: 0.7rem;
  padding-left: 1.15rem;
  margin: 1.35rem 0 0;
}

.highlight-list li {
  line-height: 1.5;
}

.badge-box,
.brand-box {
  display: grid;
  place-items: center;
  text-align: center;
  border-radius: 22px;
  background: white;
  padding: 1.4rem;
  min-height: 160px;
}

.badge-box span,
.brand-box small {
  color: #56708b;
}

.badge-box strong {
  display: grid;
  place-items: center;
  width: 90px;
  height: 90px;
  margin-top: 0.8rem;
  border-radius: 999px;
  background: #ffd44f;
  color: #0f2742;
  font-size: 2.25rem;
}

.brand-box span {
  color: #16855d;
  font-size: 1.8rem;
  font-weight: 800;
}

.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.25rem;
}

@media (max-width: 980px) {
  .hero,
  .grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .page-shell {
    padding: 1rem 0.85rem 2rem;
  }

  .hero-copy,
  .hero-panel {
    padding: 1.25rem;
  }
}
</style>
