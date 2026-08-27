<template>
  <div class="oj-shell">
    <NavBar />
    <main class="content-app">
      <router-view v-slot="{ Component }">
        <transition name="fadeInUp" mode="out-in"><component :is="Component" /></transition>
      </router-view>
      <footer class="footer">
        <p>Powered by XJU-ICTHub · Version 0.2.0</p>
      </footer>
    </main>
    <BackTop />
  </div>
</template>
<script>
import { mapActions, mapState } from '@/store/compat'
import NavBar from '@oj/components/NavBar.vue'
export default {
  name: 'app', components: { NavBar },
  created () { try { document.body.removeChild(document.getElementById('app-loader')) } catch (e) {} },
  mounted () { this.getWebsiteConfig(); this.getAuthProviders() },
  methods: { ...mapActions(['getWebsiteConfig', 'getAuthProviders', 'changeDomTitle']) },
  computed: { ...mapState(['website']) },
  watch: { website () { this.changeDomTitle() }, '$route' () { this.changeDomTitle() } }
}
</script>
<style lang="less">
.content-app { max-width: 1240px; width: 100%; margin: 0 auto; padding: 80px 24px 0; }
.footer { margin: 48px auto 18px; padding-top: 18px; border-top: 1px solid var(--color-border); text-align: center; color: var(--color-text-faint); font-size: 12px; }
.footer p { margin: 4px 0; }
.footer a { color: inherit; }
.fadeInUp-enter-active { animation: fadeInUp 220ms ease both; }
@media (max-width: 760px) { .content-app { padding: 72px 14px 0; } }
@media (prefers-reduced-motion: reduce) { .fadeInUp-enter-active { animation: none; } }
</style>
