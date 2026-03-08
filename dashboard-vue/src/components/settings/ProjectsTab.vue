<template>
  <div class="projects-tab">
    <div class="projects-layout">
      <!-- Left: project list -->
      <div class="projects-list">
        <div class="list-header">
          <h3>Projects</h3>
          <button class="btn-add" @click="showCreateForm = !showCreateForm">+ New Project</button>
        </div>

        <div v-if="showCreateForm" class="create-form">
          <input v-model="newProject.name" placeholder="Project name" class="input" />
          <input v-model="newProject.description" placeholder="Description (optional)" class="input" />
          <div class="form-actions">
            <button class="btn-primary" @click="handleCreateProject" :disabled="!newProject.name.trim()">Create</button>
            <button class="btn-ghost" @click="showCreateForm = false">Cancel</button>
          </div>
        </div>

        <div v-if="store.loading" class="loading">Loading...</div>
        <div v-else-if="store.projects.length === 0" class="empty">No projects yet</div>

        <div
          v-for="project in store.projects"
          :key="project.id"
          class="project-card"
          :class="{ active: store.selectedProject?.id === project.id }"
          @click="selectProject(project)"
        >
          <div class="project-name">{{ project.name }}</div>
          <div class="project-desc" v-if="project.description">{{ project.description }}</div>
        </div>
      </div>

      <!-- Right: project details -->
      <div class="project-detail" v-if="store.selectedProject">
        <div class="detail-header">
          <h3>{{ store.selectedProject.name }}</h3>
          <button class="btn-danger" @click="handleDeleteProject">Delete</button>
        </div>
        <p v-if="store.selectedProject.description" class="detail-desc">{{ store.selectedProject.description }}</p>

        <div class="members-section">
          <div class="members-header">
            <h4>Members</h4>
            <button class="btn-add-sm" @click="showAddMember = !showAddMember">+ Add Member</button>
          </div>

          <div v-if="showAddMember" class="add-member-form">
            <input v-model="newMember.username" placeholder="Username" class="input" />
            <select v-model="newMember.role" class="input">
              <option value="viewer">Viewer</option>
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </select>
            <button class="btn-primary" @click="handleAddMember" :disabled="!newMember.username.trim()">Add</button>
          </div>

          <div v-if="store.members.length === 0" class="empty">No members</div>
          <div v-for="member in store.members" :key="member.id" class="member-row">
            <span class="member-name">{{ member.username }}</span>
            <select
              :value="member.role"
              class="role-select"
              @change="handleRoleChange(member, $event)"
            >
              <option value="viewer">Viewer</option>
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </select>
            <button class="btn-remove" @click="handleRemoveMember(member)">Remove</button>
          </div>
        </div>
      </div>
      <div v-else class="project-detail empty-detail">
        <p>Select a project to view details</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'

const store = useAdminStore()

const showCreateForm = ref(false)
const showAddMember = ref(false)
const newProject = ref({ name: '', description: '' })
const newMember = ref({ username: '', role: 'member' })

onMounted(() => {
  store.fetchProjects()
})

async function selectProject(project) {
  store.selectedProject = project
  await store.fetchMembers(project.id)
}

async function handleCreateProject() {
  if (!newProject.value.name.trim()) return
  await store.createProject({
    name: newProject.value.name,
    description: newProject.value.description || null,
  })
  newProject.value = { name: '', description: '' }
  showCreateForm.value = false
}

async function handleDeleteProject() {
  if (!store.selectedProject) return
  await store.deleteProject(store.selectedProject.id)
}

async function handleAddMember() {
  if (!newMember.value.username.trim() || !store.selectedProject) return
  await store.addMember(store.selectedProject.id, {
    username: newMember.value.username,
    role: newMember.value.role,
  })
  newMember.value = { username: '', role: 'member' }
  showAddMember.value = false
}

async function handleRemoveMember(member) {
  if (!store.selectedProject) return
  await store.removeMember(store.selectedProject.id, member.user_id)
}

async function handleRoleChange(member, event) {
  if (!store.selectedProject) return
  await store.updateMemberRole(store.selectedProject.id, member.user_id, event.target.value)
}
</script>

<style scoped>
.projects-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 20px;
  min-height: 400px;
}

.projects-list {
  border-right: 1px solid var(--border-color);
  padding-right: 20px;
}

.list-header, .members-header, .detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.list-header h3, .detail-header h3 { margin: 0; }
.members-header h4 { margin: 0; }

.btn-add, .btn-add-sm {
  padding: 6px 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.btn-add:hover, .btn-add-sm:hover { opacity: 0.9; }

.btn-primary {
  padding: 6px 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-ghost {
  padding: 6px 14px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
}

.btn-danger {
  padding: 6px 14px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
.btn-danger:hover { background: #c0392b; }

.btn-remove {
  padding: 4px 10px;
  background: transparent;
  color: #e74c3c;
  border: 1px solid #e74c3c;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.btn-remove:hover { background: #e74c3c; color: white; }

.input {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 14px;
  margin-bottom: 8px;
}

.create-form, .add-member-form {
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  margin-bottom: 16px;
}

.add-member-form {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.add-member-form .input { margin-bottom: 0; }

.form-actions {
  display: flex;
  gap: 8px;
}

.project-card {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 8px;
  background: var(--bg-secondary);
  transition: all 0.15s;
}
.project-card:hover { background: var(--bg-tertiary); }
.project-card.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.project-name { font-weight: 600; font-size: 14px; }
.project-desc { font-size: 12px; opacity: 0.7; margin-top: 4px; }

.detail-desc { color: var(--text-secondary); margin-bottom: 20px; }

.members-section { margin-top: 24px; }

.member-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--bg-secondary);
}
.member-name { flex: 1; font-weight: 500; }

.role-select {
  padding: 4px 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-primary);
  font-size: 13px;
}

.empty-detail {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}

.loading, .empty {
  padding: 20px;
  text-align: center;
  color: var(--text-secondary);
}

@media (max-width: 768px) {
  .projects-layout {
    grid-template-columns: 1fr;
  }
  .projects-list {
    border-right: none;
    border-bottom: 1px solid var(--border-color);
    padding-right: 0;
    padding-bottom: 20px;
  }
}
</style>
