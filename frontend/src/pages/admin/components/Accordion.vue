<template>
  <div class="accordion">
    <header>
      <h2>{{title}}</h2>
      <div class="header_right">
        <slot name="header"></slot>
      </div>
    </header>
    <div class="body" v-show="isOpen">
      <slot></slot>
    </div>
    <footer @click="isOpen = !isOpen"><Icon type="arrow-down-b" :class="{'rotate': isOpen}" /></footer>
  </div>
</template>

<script>
  export default{
    name: 'Accordion',
    props: {
      title: {
        type: String,
        required: true
      }
    },
    data () {
      return {
        isOpen: true
      }
    }
  }
</script>

<style lang="less" scoped>
.accordion{
  border: 1px solid var(--color-border);
  header{
    position: relative;
    h2{
      font-size: 14px;
      margin: 0 0 0 10px;
      line-height: 50px;
    }
    .header_right{
      right: 5px;
      top: 5px;
      position: absolute;
    }
  }
  .body{
    background-color: var(--color-bg-subtle);
    border-top: 1px solid var(--color-border);
    clear: both;
    overflow: hidden;
    padding: 15px 10px;
  }
  footer{
    border-top: 1px solid var(--color-border);
    height: 36px;
    box-sizing: border-box;
    background-color: #fff;
    border-bottom-left-radius: var(--radius-md);
    border-bottom-right-radius: var(--radius-md);
    text-align: center;
    margin-top: -1px;
    color: var(--color-text-faint);
    cursor: pointer;
    transition: .2s;
    &:hover{
    background-color: var(--color-bg-subtle);
    }
    :deep(.legacy-icon) { transition: transform var(--transition); }
    .rotate{ transform: rotate(180deg); }
  }
}
</style>
