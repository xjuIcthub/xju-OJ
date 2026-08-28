<template>
  <span class="user-avatar-display" :style="avatarStyle" role="img" :aria-label="alt || username">
    <img v-if="src && !imageFailed"
         :key="src"
         :src="src"
         :alt="alt || username"
         @load="imageFailed = false"
         @error="imageFailed = true">
    <span v-else class="user-avatar-fallback" aria-hidden="true">{{ initial }}</span>
  </span>
</template>

<script>
  export default {
    name: 'UserAvatar',
    props: {
      src: {
        type: String,
        default: ''
      },
      username: {
        type: String,
        default: ''
      },
      alt: {
        type: String,
        default: ''
      },
      size: {
        type: Number,
        default: 32
      }
    },
    data () {
      return {
        imageFailed: false
      }
    },
    computed: {
      avatarStyle () {
        return {
          width: `${this.size}px`,
          height: `${this.size}px`,
          fontSize: `${Math.max(11, Math.round(this.size * 0.32))}px`
        }
      },
      initial () {
        return (this.username || '?').slice(0, 1).toUpperCase()
      }
    },
    watch: {
      src () {
        this.imageFailed = false
      }
    }
  }
</script>

<style scoped lang="less">
  .user-avatar-display {
    display: inline-grid;
    flex: none;
    overflow: hidden;
    place-items: center;
    border-radius: 50%;
    background: var(--color-bg-subtle);
    color: var(--color-text);
    vertical-align: middle;
  }

  img,
  .user-avatar-fallback {
    display: block;
    width: 100%;
    height: 100%;
  }

  img {
    object-fit: cover;
  }

  .user-avatar-fallback {
    display: grid;
    place-items: center;
    font-size: 1em;
    font-weight: 650;
    line-height: 1;
  }
</style>
