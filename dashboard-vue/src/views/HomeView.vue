<template>
  <div class="home-page">
    <div class="home-hero">
      <h1 class="home-title">ErrorLens</h1>
      <p class="home-subtitle">AI-powered QA Platform</p>
    </div>
    <div class="home-cards">
      <div class="home-card" @click="router.push('/qa')">
        <div class="card-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2h6l3 7H6L9 2z"/><path d="M12 9v13"/><path d="M8 22h8"/><path d="M5 12l-2 4h18l-2-4"/></svg>
        </div>
        <div class="card-body">
          <div class="card-title">QA</div>
          <div class="card-desc">Test cases, plans and runs</div>
        </div>
        <div class="card-arrow">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
        </div>
      </div>
      <div class="home-card" @click="router.push('/issues')">
        <div class="card-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 8h7"/><path d="M9 12h7"/><path d="M9 16h4"/></svg>
        </div>
        <div class="card-body">
          <div class="card-title">Issues</div>
          <div class="card-desc">Tasks and bug tracker</div>
        </div>
        <div class="card-arrow">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
        </div>
      </div>
      <div class="home-card" @click="router.push('/articles')">
        <div class="card-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/><path d="M8 7h6"/><path d="M8 11h8"/></svg>
        </div>
        <div class="card-body">
          <div class="card-title">Articles</div>
          <div class="card-desc">Team knowledge base</div>
        </div>
        <div class="card-arrow">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 60px);
  padding: 40px 20px;
}

.home-hero {
  text-align: center;
  margin-bottom: 48px;
}

.home-title {
  font-size: 40px;
  font-weight: 700;
  margin: 0 0 8px;
  color: var(--text-primary);
}

.home-subtitle {
  font-size: 16px;
  color: var(--text-secondary);
  margin: 0;
}

.home-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  width: 100%;
  max-width: 900px;
}

.home-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 28px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.home-card:hover {
  border-color: var(--accent);
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.card-icon {
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: rgba(124, 92, 191, 0.12);
  border-radius: 12px;
  color: var(--accent);
}

.card-body {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.card-desc {
  font-size: 13px;
  color: var(--text-secondary);
}

.card-arrow {
  color: var(--accent);
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

@media (max-width: 768px) {
  .home-cards {
    grid-template-columns: 1fr;
  }
}
</style>
