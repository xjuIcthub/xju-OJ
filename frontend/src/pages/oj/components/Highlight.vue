<template>
  <div class="highlight-shell">
    <pre v-highlight="code"><code :class="languageClass"></code></pre>
  </div>
</template>

<script>
  export default {
    name: 'highlight',
    props: {
      language: {
        type: String
      },
      code: {
        required: true,
        type: String
      }
    },
    computed: {
      languageClass () {
        const normalized = String(this.language || '').toLowerCase()
        const languageMap = {
          'c': 'cpp',
          'c++': 'cpp',
          'python2': 'python',
          'python3': 'python',
          'java': 'java'
        }
        return `language-${languageMap[normalized] || normalized || 'plaintext'}`
      }
    }
  }
</script>

<style scoped lang="less">
  .highlight-shell {
    overflow: hidden;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: #fdf6e3;
  }

  pre {
    display: block;
    overflow: auto;
    margin: 0;
    padding: 0;
    border: 0;
    background: #fdf6e3;
  }

  :deep(code.hljs) {
    display: block;
    min-height: 180px;
    padding: 20px 22px;
    border: 0;
    background: #fdf6e3;
    color: #586e75;
    font-family: "JetBrainsMono Nerd Font", "JetBrains Mono", "FiraCode Nerd Font", "Fira Code", Consolas, monospace;
    font-size: 13px;
    line-height: 1.7;
    tab-size: 4;
  }

  @media (max-width: 760px) {
    :deep(code.hljs) { min-height: 150px; padding: 16px; font-size: 12px; }
  }
</style>
