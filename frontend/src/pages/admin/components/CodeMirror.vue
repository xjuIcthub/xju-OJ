<template><CodeMirrorAdapter :value="content" :mode="mode" :line-wrapping="false" autofocus @input="onInput" /></template>
<script>
import CodeMirrorAdapter from '@/shared/editors/CodeMirrorAdapter.vue'
export default {
  name: 'CodeMirror', components: { CodeMirrorAdapter },
  props: { value: { type: String, default: '' }, modelValue: { type: String, default: undefined }, mode: { type: String, default: 'text/x-csrc' } },
  computed: { content () { return this.modelValue === undefined ? this.value : this.modelValue } },
  emits: ['change', 'input', 'update:value', 'update:modelValue'],
  methods: { onInput (value) { this.$emit('change', value); this.$emit('input', value); this.$emit('update:value', value); this.$emit('update:modelValue', value) } }
}
</script>
