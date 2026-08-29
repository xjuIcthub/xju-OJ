<template>
  <div class="icon-btn-wrap">
    <el-tooltip class="item" effect="dark" :content="name" placement="top">
      <el-button text :class="['icon-btn-control', { 'is-danger': danger }]" size="small" :aria-label="name">
        <Icon :type="icon" />
      </el-button>
    </el-tooltip>
  </div>
</template>

<script>
  export default {
    name: 'IconBtn',
    props: {
      name: {
        type: String,
        required: true
      },
      icon: {
        type: String,
        required: true
      },
      danger: {
        type: Boolean,
        default: false
      }
    }
  }
</script>

<style scoped lang="less">
.icon-btn-wrap { display: inline-flex; vertical-align: middle; }
.icon-btn-control {
  width: 30px;
  height: 30px;
  min-height: 30px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-muted);
}
.icon-btn-control:hover,
.icon-btn-control:focus-visible {
  color: var(--color-text);
  border-color: var(--color-border);
  background: var(--color-bg-subtle);
}
.icon-btn-control.is-danger { color: var(--oj-danger); }
.icon-btn-control.is-danger:hover,
.icon-btn-control.is-danger:focus-visible {
  color: var(--oj-danger);
  border-color: rgba(224, 62, 62, .28);
  background: var(--tag-research-bg);
}
</style>
