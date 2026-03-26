<template>
  <div class="home-page">
    <div class="home-hero">
      <h1 class="home-title">ErrorLens</h1>
      <p class="home-subtitle">AI-powered QA Platform</p>
    </div>
    <div class="home-cards">
      <div class="home-card" @click="router.push('/qa')">
        <div class="card-icon">&#x1F9EA;</div>
        <div class="card-body">
          <div class="card-title">QA</div>
          <div class="card-desc">Test cases, plans and runs</div>
        </div>
        <div class="card-arrow">&rarr;</div>
      </div>
      <div class="home-card" @click="router.push('/issues')">
        <div class="card-icon">&#x1F4CB;</div>
        <div class="card-body">
          <div class="card-title">Issues</div>
          <div class="card-desc">Tasks and bug tracker</div>
        </div>
        <div class="card-arrow">&rarr;</div>
      </div>
      <div class="home-card" @click="router.push('/articles')">
        <div class="card-icon">&#x1F4DA;</div>
        <div class="card-body">
          <div class="card-title">Articles</div>
          <div class="card-desc">Team knowledge base</div>
        </div>
        <div class="card-arrow">&rarr;</div>
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
  font-size: 32px;
  flex-shrink: 0;
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
  font-size: 20px;
  color: var(--accent);
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .home-cards {
    grid-template-columns: 1fr;
  }
}
</style>
