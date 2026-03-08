import { Node, mergeAttributes } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import Suggestion from '@tiptap/suggestion'
import EntityMentionChip from '../EntityMentionChip.vue'

export default Node.create({
  name: 'entityMention',
  group: 'inline',
  inline: true,
  atom: true,

  addAttributes() {
    return {
      entityType: { default: null },
      entityId: { default: null },
      entityTitle: { default: null },
      linkType: { default: 'related' },
    }
  },

  parseHTML() {
    return [{ tag: 'span[data-entity-mention]' }]
  },

  renderHTML({ node, HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        'data-entity-mention': '',
        'data-entity-type': node.attrs.entityType,
        'data-entity-id': node.attrs.entityId,
        'data-entity-title': node.attrs.entityTitle,
        'data-link-type': node.attrs.linkType,
      }),
      node.attrs.entityTitle || 'Unknown',
    ]
  },

  addNodeView() {
    return VueNodeViewRenderer(EntityMentionChip)
  },

  addCommands() {
    return {
      insertEntityMention: (attrs) => ({ chain }) => {
        return chain()
          .insertContent({
            type: this.name,
            attrs,
          })
          .run()
      },
    }
  },

  addProseMirrorPlugins() {
    return [
      Suggestion({
        editor: this.editor,
        char: '@',
        command: ({ editor, range, props }) => {
          editor
            .chain()
            .focus()
            .deleteRange(range)
            .insertContent({
              type: 'entityMention',
              attrs: {
                entityType: props.entityType,
                entityId: props.entityId,
                entityTitle: props.entityTitle,
                linkType: props.linkType || 'related',
              },
            })
            .run()
        },
        ...this.options.suggestion,
      }),
    ]
  },

  addOptions() {
    return {
      suggestion: {
        char: '@',
        pluginKey: 'entityMentionSuggestion',
        command: ({ editor, range, props }) => {
          editor
            .chain()
            .focus()
            .deleteRange(range)
            .insertContent({
              type: 'entityMention',
              attrs: {
                entityType: props.entityType,
                entityId: props.entityId,
                entityTitle: props.entityTitle,
                linkType: props.linkType || 'related',
              },
            })
            .run()
        },
      },
    }
  },
})
