<template>
  <div class="breadcrumb">
    <el-breadcrumb separator=">">
      <el-breadcrumb-item :to="{ path: '/' }">XJU-OJ</el-breadcrumb-item>
      <el-breadcrumb-item><slot name="topNavName">PLEASE OVERIDE ME</slot></el-breadcrumb-item>
    </el-breadcrumb>
  </div>
</template>

<style scoped lang="less">
  .breadcrumb {
    margin: 10px 14px 20px;
    padding: 13px 16px;
    background-color: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-card);
  }
  :deep(.el-breadcrumb__inner) { color: var(--color-text-muted); font-weight: 500; }
  :deep(.el-breadcrumb__inner.is-link:hover) { color: var(--color-link); }
</style>
