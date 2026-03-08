<template>
  <div class="rich-editor" :class="{ 'rich-editor--readonly': !editable }">
    <EditorToolbar
      v-if="editable"
      :editor="editor"
      :uploadEnabled="uploadEnabled"
      @upload-image="triggerImageUpload"
    />
    <EditorContent :editor="editor" class="rich-editor__content" />
    <div v-if="maxLength" class="rich-editor__counter">
      {{ characterCount }} / {{ maxLength }}
    </div>
    <input
      v-if="uploadEnabled"
      ref="imageInput"
      type="file"
      accept="image/*"
      style="display: none"
      @change="handleImageSelect"
    />
    <Teleport to="body">
      <EntityMentionPopup />
    </Teleport>
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import Placeholder from '@tiptap/extension-placeholder'
import CharacterCount from '@tiptap/extension-character-count'
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight'
import { common, createLowlight } from 'lowlight'
import EditorToolbar from './EditorToolbar.vue'
import EntityMentionPopup from './EntityMentionPopup.vue'
import EntityMention from './extensions/EntityMention.js'
import entityMentionSuggestion from './EntityMentionSuggestion.js'
import { articlesApi } from '@/services/api'
import '@/assets/rich-editor.css'

const lowlight = createLowlight(common)

const props = defineProps({
  modelValue: { type: Object, default: null },
  placeholder: { type: String, default: 'Начните писать...' },
  editable: { type: Boolean, default: true },
  uploadEnabled: { type: Boolean, default: false },
  maxLength: { type: Number, default: null }
})

const emit = defineEmits(['update:modelValue', 'word-count'])

const imageInput = ref(null)
const characterCount = ref(0)

const extensions = [
  StarterKit.configure({
    codeBlock: false
  }),
  Image,
  Placeholder.configure({
    placeholder: props.placeholder
  }),
  CodeBlockLowlight.configure({ lowlight }),
  EntityMention.configure({
    suggestion: entityMentionSuggestion,
  }),
  ...(props.maxLength
    ? [CharacterCount.configure({ limit: props.maxLength })]
    : [CharacterCount])
]

const editor = useEditor({
  extensions,
  content: props.modelValue,
  editable: props.editable,
  onUpdate: ({ editor: ed }) => {
    const json = ed.getJSON()
    emit('update:modelValue', json)

    const storage = ed.storage.characterCount
    const chars = storage.characters()
    const words = storage.words()
    characterCount.value = chars
    emit('word-count', { words, characters: chars })
  }
})

watch(
  () => props.modelValue,
  (newVal) => {
    if (!editor.value) return
    const currentJson = JSON.stringify(editor.value.getJSON())
    const newJson = JSON.stringify(newVal)
    if (currentJson !== newJson) {
      editor.value.commands.setContent(newVal, false)
    }
  }
)

watch(
  () => props.editable,
  (val) => {
    if (editor.value) {
      editor.value.setEditable(val)
    }
  }
)

function triggerImageUpload() {
  imageInput.value?.click()
}

async function handleImageSelect(event) {
  const file = event.target.files?.[0]
  if (!file || !editor.value) return

  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await articlesApi.uploadImage(formData)
    const { url } = response.data
    editor.value.chain().focus().setImage({ src: url }).run()
  } catch (err) {
    console.error('Image upload failed:', err)
  } finally {
    event.target.value = ''
  }
}

onBeforeUnmount(() => {
  editor.value?.destroy()
})
</script>
