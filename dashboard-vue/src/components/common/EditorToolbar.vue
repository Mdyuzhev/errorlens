<template>
  <div class="editor-toolbar" v-if="editor">
    <!-- Group 1: Text formatting -->
    <div class="toolbar-group">
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: editor.isActive('bold') }"
        @click="editor.chain().focus().toggleBold().run()"
        title="Bold"
      >
        <strong>B</strong>
      </button>
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: editor.isActive('italic') }"
        @click="editor.chain().focus().toggleItalic().run()"
        title="Italic"
      >
        <em>I</em>
      </button>
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: editor.isActive('code') }"
        @click="editor.chain().focus().toggleCode().run()"
        title="Inline Code"
      >
        <span class="mono">&lt;/&gt;</span>
      </button>
    </div>

    <!-- Group 2: Structure -->
    <div class="toolbar-group">
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: editor.isActive('heading', { level: 1 }) }"
        @click="editor.chain().focus().toggleHeading({ level: 1 }).run()"
        title="Heading 1"
      >
        H1
      </button>
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: editor.isActive('heading', { level: 2 }) }"
        @click="editor.chain().focus().toggleHeading({ level: 2 }).run()"
        title="Heading 2"
      >
        H2
      </button>
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: editor.isActive('heading', { level: 3 }) }"
        @click="editor.chain().focus().toggleHeading({ level: 3 }).run()"
        title="Heading 3"
      >
        H3
      </button>
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: editor.isActive('bulletList') }"
        @click="editor.chain().focus().toggleBulletList().run()"
        title="Bullet List"
      >
        &#8226;
      </button>
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: editor.isActive('orderedList') }"
        @click="editor.chain().focus().toggleOrderedList().run()"
        title="Ordered List"
      >
        1.
      </button>
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: editor.isActive('blockquote') }"
        @click="editor.chain().focus().toggleBlockquote().run()"
        title="Blockquote"
      >
        &#8220;
      </button>
    </div>

    <!-- Group 3: Insert -->
    <div class="toolbar-group">
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: editor.isActive('codeBlock') }"
        @click="editor.chain().focus().toggleCodeBlock().run()"
        title="Code Block"
      >
        { }
      </button>
      <button
        type="button"
        class="toolbar-btn"
        @click="editor.chain().focus().setHorizontalRule().run()"
        title="Horizontal Rule"
      >
        &#8212;
      </button>
      <button
        v-if="uploadEnabled"
        type="button"
        class="toolbar-btn"
        @click="$emit('upload-image')"
        title="Insert Image"
        data-testid="image-upload-btn"
      >
        IMG
      </button>
    </div>

    <!-- Group 4: History -->
    <div class="toolbar-group">
      <button
        type="button"
        class="toolbar-btn"
        :disabled="!editor.can().undo()"
        @click="editor.chain().focus().undo().run()"
        title="Undo"
      >
        &#8617;
      </button>
      <button
        type="button"
        class="toolbar-btn"
        :disabled="!editor.can().redo()"
        @click="editor.chain().focus().redo().run()"
        title="Redo"
      >
        &#8618;
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  editor: { type: Object, default: null },
  uploadEnabled: { type: Boolean, default: false }
})

defineEmits(['upload-image'])
</script>

<style scoped>
.editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px;
  border: 1px solid var(--border-color);
  border-bottom: none;
  border-radius: 8px 8px 0 0;
  background: var(--bg-secondary);
}

.toolbar-group {
  display: flex;
  gap: 2px;
  padding-right: 8px;
  border-right: 1px solid var(--border-color);
}

.toolbar-group:last-child {
  border-right: none;
  padding-right: 0;
}

.toolbar-btn {
  background: none;
  border: 1px solid transparent;
  color: var(--text-secondary);
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  min-width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.toolbar-btn:hover {
  background: var(--accent);
  color: white;
}

.toolbar-btn.active {
  background: var(--accent);
  color: white;
}

.toolbar-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.toolbar-btn:disabled:hover {
  background: none;
  color: var(--text-secondary);
}

.mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}
</style>
