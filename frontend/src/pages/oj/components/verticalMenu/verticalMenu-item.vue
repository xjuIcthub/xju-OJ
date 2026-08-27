<template>
  <li @click.stop="handleClick" :class="{disabled: disabled}">
    <slot></slot>
  </li>
</template>

<script>
  import Emitter from '../mixins/emitter'

  export default {
    name: 'VerticalMenu-item',
    mixins: [Emitter],
    props: {
      route: {
        type: [String, Object]
      },
      disabled: {
        type: Boolean,
        default: false
      }
    },
    methods: {
      handleClick () {
        if (this.route) {
          this.dispatch('VerticalMenu', 'on-click', this.route)
        }
      }
    }
  }
</script>

<style scoped lang="less">
  .disabled {
    /*background-color: #ccc;*/
    opacity: 1;
    /*cursor: not-allowed;*/
    pointer-events: none;
    color: #ccc;
    &:hover {
      border-left: none;
      color: #ccc;
      background: #fff;
    }
  }

  li {
    border-bottom: 1px solid var(--color-border);
    color: var(--color-text-muted);
    display: block;
    text-align: left;
    padding: 15px 20px;
    &:hover {
      background: var(--color-bg-subtle);
      border-left: 2px solid var(--color-text);
      color: var(--color-text);
    }
    & > .ivu-icon, & > .legacy-icon {
      font-size: 16px;
      margin-right: 8px;
    }
    &:last-child {
      border-bottom: none;
    }
  }
</style>
