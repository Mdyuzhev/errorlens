<template>
  <div class="activity-feed">
    <h3>Activity</h3>

    <!-- Feed items -->
    <div class="feed-list">
      <div v-for="item in activity" :key="item.id" class="feed-item" :class="item.entry_type">
        <!-- Activity entry -->
        <template v-if="item.entry_type === 'activity'">
          <div class="feed-icon activity-icon">
            <AppIcon :name="getActivityIcon(item.action_type)" :size="14" />
          </div>
          <div class="feed-content">
            <span class="actor">{{ item.actor?.display_name || item.actor?.username || 'System' }}</span>
            <span class="action-text">{{ formatAction(item) }}</span>
            <span class="feed-time">{{ timeAgo(item.created_at) }}</span>
          </div>
        </template>

        <!-- Comment entry -->
        <template v-else>
          <div class="feed-icon comment-icon">
            <span class="avatar-sm">{{ (item.author?.username || '?')[0].toUpperCase() }}</span>
          </div>
          <div class="feed-content comment-content">
            <div class="comment-header">
              <span class="actor">{{ item.author?.display_name || item.author?.username }}</span>
              <span class="feed-time">{{ timeAgo(item.created_at) }}</span>
              <span v-if="item.is_edited" class="edited-badge">edited</span>
            </div>
            <div class="comment-body" v-if="editingCommentId !== item.id">
              <RichEditor
                v-if="isJsonContent(item.content)"
                :modelValue="parseContent(item.content)"
                :editable="false"
                :showToolbar="false"
              />
              <p v-else>{{ item.content }}</p>
            </div>
            <div v-else class="comment-edit">
              <textarea v-model="editCommentContent" rows="3"></textarea>
              <div class="comment-edit-actions">
                <button class="btn-xs" @click="saveEditComment(item)">Save</button>
                <button class="btn-xs btn-ghost" @click="editingCommentId = null">Cancel</button>
              </div>
            </div>
            <div v-if="canEditComment(item) && editingCommentId !== item.id" class="comment-actions">
              <button class="btn-link" @click="startEditComment(item)">Edit</button>
              <button class="btn-link danger" @click="deleteComment(item)">Delete</button>
            </div>
          </div>
        </template>
      </div>

      <div v-if="!activity.length" class="empty-feed">
        No activity yet
      </div>
    </div>

    <!-- Add comment form -->
    <div class="add-comment">
      <textarea
        v-model="newComment"
        placeholder="Add a comment..."
        rows="3"
        @keydown.ctrl.enter="submitComment"
      ></textarea>
      <button class="btn btn-primary btn-sm" @click="submitComment" :disabled="!newComment.trim()">
        Comment
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { tasksApi } from '@/services/api'
import RichEditor from '@/components/common/RichEditor.vue'
import AppIcon from '@/components/common/AppIcon.vue'

const props = defineProps({
  taskId: { type: String, required: true },
  activity: { type: Array, default: () => [] },
})

const emit = defineEmits(['comment-added'])

const auth = useAuthStore()
const newComment = ref('')
const editingCommentId = ref(null)
const editCommentContent = ref('')

function isJsonContent(content) {
  if (!content) return false
  try {
    const parsed = JSON.parse(content)
    return parsed?.type === 'doc'
  } catch { return false }
}

function parseContent(raw) {
  try { return JSON.parse(raw) } catch { return null }
}

function getActivityIcon(actionType) {
  const map = {
    created: 'plus',
    status_changed: 'arrow-right',
    field_updated: 'edit',
    assigned: 'user',
    commented: 'message-square',
  }
  return map[actionType] || 'activity'
}

function formatAction(item) {
  switch (item.action_type) {
    case 'created':
      return 'created this task'
    case 'status_changed':
      return `changed status from ${item.old_value?.status || '?'} to ${item.new_value?.status || '?'}`
    case 'field_updated':
      return `changed ${item.field_name} from "${item.old_value?.value || '-'}" to "${item.new_value?.value || '-'}"`
    case 'assigned':
      return 'changed the assignee'
    case 'commented':
      return 'added a comment'
    default:
      return item.action_type
  }
}

function timeAgo(dateStr) {
  const date = new Date(dateStr)
  const now = new Date()
  const seconds = Math.floor((now - date) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  return date.toLocaleDateString()
}

function canEditComment(item) {
  return item.author?.id === auth.user?.id || auth.user?.is_admin
}

function startEditComment(item) {
  editingCommentId.value = item.id
  editCommentContent.value = item.content
}

async function saveEditComment(item) {
  try {
    await tasksApi.updateComment(props.taskId, item.id, editCommentContent.value)
    editingCommentId.value = null
    emit('comment-added')
  } catch {}
}

async function deleteComment(item) {
  if (!confirm('Delete this comment?')) return
  try {
    await tasksApi.deleteComment(props.taskId, item.id)
    emit('comment-added')
  } catch {}
}

async function submitComment() {
  if (!newComment.value.trim()) return
  try {
    await tasksApi.createComment(props.taskId, newComment.value)
    newComment.value = ''
    emit('comment-added')
  } catch {}
}
</script>

<style scoped>
.activity-feed {
  margin-top: 32px;
}

.activity-feed h3 {
  font-size: 16px;
  margin: 0 0 16px 0;
}

.feed-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.feed-item {
  display: flex;
  gap: 12px;
  padding: 10px 0;
}

.feed-item.activity {
  padding: 6px 0;
}

.feed-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.activity-icon {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.avatar-sm {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--accent);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
}

.feed-content {
  flex: 1;
  min-width: 0;
}

.feed-item.activity .feed-content {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 13px;
  color: var(--text-secondary);
}

.actor {
  font-weight: 600;
  color: var(--text-primary);
}

.feed-time {
  font-size: 11px;
  color: var(--text-secondary);
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.edited-badge {
  font-size: 10px;
  color: var(--text-secondary);
  font-style: italic;
}

.comment-body {
  background: var(--bg-card);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.5;
}

.comment-body p { margin: 0; }

.comment-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.btn-link {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  padding: 2px;
}

.btn-link:hover { color: var(--text-primary); }
.btn-link.danger:hover { color: #ef4444; }

.comment-edit textarea {
  width: 100%;
  border: 1px solid var(--bg-secondary);
  border-radius: 6px;
  padding: 8px;
  font-size: 13px;
  background: var(--bg-card);
  color: var(--text-primary);
  resize: vertical;
}

.comment-edit-actions {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}

.btn-xs {
  padding: 4px 10px;
  font-size: 11px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  background: var(--accent);
  color: white;
}

.btn-xs.btn-ghost {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.empty-feed {
  padding: 20px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}

.add-comment {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--bg-secondary);
}

.add-comment textarea {
  width: 100%;
  border: 1px solid var(--bg-secondary);
  border-radius: 8px;
  padding: 10px;
  font-size: 14px;
  background: var(--bg-card);
  color: var(--text-primary);
  resize: vertical;
  margin-bottom: 8px;
}

.add-comment textarea:focus {
  outline: none;
  border-color: var(--accent);
}

.btn-sm {
  padding: 8px 16px;
  font-size: 13px;
}
</style>
