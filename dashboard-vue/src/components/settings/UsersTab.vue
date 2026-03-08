<template>
  <div class="users-tab">
    <!-- Create user form -->
    <div class="create-section">
      <button class="btn-toggle" @click="showCreateForm = !showCreateForm">
        {{ showCreateForm ? 'Hide Form' : '+ Create User' }}
      </button>

      <div v-if="showCreateForm" class="create-form">
        <div class="form-row">
          <div class="form-field">
            <label>Username</label>
            <input v-model="newUser.username" placeholder="Min 3 characters" class="input" />
          </div>
          <div class="form-field">
            <label>Password</label>
            <input v-model="newUser.password" type="password" placeholder="Min 6 characters" class="input" />
          </div>
          <div class="form-field checkbox-field">
            <label>
              <input type="checkbox" v-model="newUser.is_admin" /> Admin
            </label>
          </div>
          <button
            class="btn-primary"
            @click="handleCreateUser"
            :disabled="!isFormValid"
          >
            Create User
          </button>
        </div>
        <p v-if="createError" class="error-msg">{{ createError }}</p>
      </div>
    </div>

    <!-- Users table -->
    <div v-if="store.loading" class="loading">Loading...</div>
    <table v-else class="users-table">
      <thead>
        <tr>
          <th>Username</th>
          <th>Admin</th>
          <th>Active</th>
          <th>Last Login</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in store.users" :key="user.id">
          <td class="username-cell">{{ user.username }}</td>
          <td>
            <span :class="user.is_admin ? 'badge-admin' : 'badge-user'">
              {{ user.is_admin ? 'Admin' : 'User' }}
            </span>
          </td>
          <td>
            <label class="toggle-switch" v-if="user.id !== currentUserId">
              <input
                type="checkbox"
                :checked="user.is_active"
                @change="handleToggleActive(user)"
              />
              <span class="toggle-slider"></span>
            </label>
            <span v-else class="badge-self">You</span>
          </td>
          <td class="date-cell">{{ formatDate(user.last_login) }}</td>
          <td>
            <div class="action-cell" v-if="user.id !== currentUserId">
              <button
                v-if="passwordEditId !== user.id"
                class="btn-action"
                @click="passwordEditId = user.id"
              >
                Change Password
              </button>
              <div v-else class="password-inline">
                <input
                  v-model="newPassword"
                  type="password"
                  placeholder="New password (min 6)"
                  class="input input-sm"
                />
                <button class="btn-action btn-save" @click="handleChangePassword(user.id)" :disabled="newPassword.length < 6">Save</button>
                <button class="btn-action" @click="passwordEditId = null; newPassword = ''">Cancel</button>
              </div>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { useAuthStore } from '@/stores/auth'

const store = useAdminStore()
const auth = useAuthStore()

const showCreateForm = ref(false)
const createError = ref('')
const newUser = ref({ username: '', password: '', is_admin: false })
const passwordEditId = ref(null)
const newPassword = ref('')

const currentUserId = computed(() => auth.user?.id)
const isFormValid = computed(() => newUser.value.username.length >= 3 && newUser.value.password.length >= 6)

onMounted(() => {
  store.fetchUsers()
})

function formatDate(dateStr) {
  if (!dateStr) return 'Never'
  return new Date(dateStr).toLocaleString()
}

async function handleCreateUser() {
  if (!isFormValid.value) return
  createError.value = ''
  try {
    await store.createUser({
      username: newUser.value.username,
      password: newUser.value.password,
      is_admin: newUser.value.is_admin,
    })
    newUser.value = { username: '', password: '', is_admin: false }
    showCreateForm.value = false
  } catch (err) {
    createError.value = err.response?.data?.detail || 'Failed to create user'
  }
}

async function handleChangePassword(userId) {
  if (newPassword.value.length < 6) return
  try {
    await store.changePassword(userId, newPassword.value)
    passwordEditId.value = null
    newPassword.value = ''
  } catch (err) {
    createError.value = err.response?.data?.detail || 'Failed to change password'
  }
}

async function handleToggleActive(user) {
  await store.toggleActive(user.id, !user.is_active)
}
</script>

<style scoped>
.create-section { margin-bottom: 20px; }

.btn-toggle {
  padding: 8px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}
.btn-toggle:hover { opacity: 0.9; }

.create-form {
  margin-top: 12px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.form-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.form-field { display: flex; flex-direction: column; gap: 4px; }
.form-field label { font-size: 12px; color: var(--text-secondary); }

.checkbox-field {
  justify-content: flex-end;
  padding-bottom: 8px;
}
.checkbox-field label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--text-primary);
  cursor: pointer;
}

.input {
  padding: 8px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 14px;
}
.input-sm { padding: 4px 8px; font-size: 13px; }

.btn-primary {
  padding: 8px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.error-msg {
  color: #e74c3c;
  font-size: 13px;
  margin-top: 8px;
}

.users-table {
  width: 100%;
  border-collapse: collapse;
}

.users-table th {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 2px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.users-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--bg-secondary);
  font-size: 14px;
}

.username-cell { font-weight: 500; }
.date-cell { color: var(--text-secondary); font-size: 13px; }

.badge-admin {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.badge-user {
  background: var(--bg-secondary);
  color: var(--text-secondary);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.badge-self {
  color: var(--text-secondary);
  font-size: 12px;
  font-style: italic;
}

/* Toggle switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
}
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background: #ccc;
  border-radius: 22px;
  transition: 0.2s;
}
.toggle-slider::before {
  content: '';
  position: absolute;
  height: 16px; width: 16px;
  left: 3px; bottom: 3px;
  background: white;
  border-radius: 50%;
  transition: 0.2s;
}
.toggle-switch input:checked + .toggle-slider {
  background: #4CAF50;
}
.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(18px);
}

.action-cell { display: flex; gap: 8px; align-items: center; }

.btn-action {
  padding: 4px 10px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
}
.btn-action:hover { background: var(--bg-tertiary); }
.btn-action.btn-save {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}
.btn-action:disabled { opacity: 0.5; cursor: not-allowed; }

.password-inline { display: flex; gap: 6px; align-items: center; }

.loading { padding: 40px; text-align: center; color: var(--text-secondary); }
</style>
