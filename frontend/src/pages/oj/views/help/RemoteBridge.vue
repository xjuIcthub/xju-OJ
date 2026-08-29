<template>
  <div class="remote-bridge-page">
    <Panel :padding="24" class="bridge-panel">
      <template #title><div>{{ $t('m.Remote_Bridge') }}</div></template>

      <section class="bridge-hero">
        <div class="bridge-copy">
          <span class="eyebrow">ScriptCat Userscript</span>
          <h1>{{ $t('m.Remote_Bridge_Title') }}</h1>
          <p>{{ $t('m.Remote_Bridge_Intro') }}</p>
        </div>
        <div class="bridge-status" :class="bridgeStatusClass">
          <span class="status-dot" aria-hidden="true"></span>
          <div>
            <strong>{{ bridgeStatusLabel }}</strong>
            <small v-if="bridgeDetected">v{{ bridgeVersion }}</small>
          </div>
        </div>
      </section>

      <ol class="install-steps">
        <li>
          <span class="step-number">1</span>
          <div>
            <h2>{{ $t('m.Remote_Bridge_Step_ScriptCat') }}</h2>
            <p>{{ $t('m.Remote_Bridge_Step_ScriptCat_Hint') }}</p>
            <a class="bridge-button secondary" :href="scriptCatUrl" target="_blank" rel="noopener noreferrer">
              {{ $t('m.Remote_Bridge_Install_ScriptCat') }}
            </a>
          </div>
        </li>
        <li>
          <span class="step-number">2</span>
          <div>
            <h2>{{ $t('m.Remote_Bridge_Step_Userscript') }}</h2>
            <p>{{ $t('m.Remote_Bridge_Step_Userscript_Hint') }}</p>
            <a class="bridge-button primary" :href="userscriptUrl" target="_blank" rel="noopener noreferrer"
               @click="beginUserscriptActivation">
              {{ bridgeDetected ? $t('m.Remote_Bridge_Update_Userscript') : $t('m.Remote_Bridge_Install_Userscript') }}
            </a>
          </div>
        </li>
        <li>
          <span class="step-number">3</span>
          <div>
            <h2>{{ $t('m.Remote_Bridge_Step_Login') }}</h2>
            <p>{{ $t('m.Remote_Bridge_Step_Login_Hint') }}</p>
            <div class="provider-list" aria-label="Supported providers">
              <span>洛谷</span><span>牛客</span><span>Codeforces</span>
            </div>
          </div>
        </li>
      </ol>

      <aside class="privacy-note">
        <strong>{{ $t('m.Remote_Bridge_Privacy_Title') }}</strong>
        <p>{{ $t('m.Remote_Bridge_Privacy') }}</p>
      </aside>
    </Panel>
  </div>
</template>

<script>
import {
  isRemoteBridgeDetected,
  isRemoteBridgeInstalled,
  remoteBridgeVersion,
  requestRemoteBridgeStatus,
  subscribeRemoteBridgeReady
} from '@oj/remoteBridge'

export default {
  name: 'RemoteBridge',
  data () {
    return {
      bridgeDetected: false,
      bridgeInstalled: false,
      bridgeVersion: '',
      checkTimer: null,
      activationPending: false,
      activationVersion: '',
      activationCheckTimer: null,
      unsubscribeBridgeReady: null,
      scriptCatUrl: 'https://microsoftedge.microsoft.com/addons/detail/scriptcat/liilgpjgabokdklappibcjfablkpcekh',
      userscriptUrl: '/static/userscripts/xju-oj-remote-bridge.user.js'
    }
  },
  computed: {
    bridgeStatusClass () {
      if (this.bridgeInstalled) return 'is-installed'
      return this.bridgeDetected ? 'is-outdated' : 'is-missing'
    },
    bridgeStatusLabel () {
      if (this.bridgeInstalled) return this.$t('m.Remote_Bridge_Installed')
      return this.bridgeDetected ? this.$t('m.Remote_Bridge_Outdated') : this.$t('m.Remote_Bridge_Missing')
    }
  },
  mounted () {
    this.unsubscribeBridgeReady = subscribeRemoteBridgeReady(this.handleBridgeReady)
    window.addEventListener('focus', this.handleActivationReturn)
    document.addEventListener('visibilitychange', this.handleActivationReturn)
    this.checkBridge()
    requestRemoteBridgeStatus()
    this.checkTimer = window.setInterval(this.checkBridge, 1000)
  },
  beforeUnmount () {
    if (this.unsubscribeBridgeReady) this.unsubscribeBridgeReady()
    window.removeEventListener('focus', this.handleActivationReturn)
    document.removeEventListener('visibilitychange', this.handleActivationReturn)
    if (this.checkTimer) window.clearInterval(this.checkTimer)
    if (this.activationCheckTimer) window.clearTimeout(this.activationCheckTimer)
  },
  methods: {
    handleBridgeReady (detail) {
      const version = detail && detail.version
      if (version) this.setInstalled(version)
      else this.checkBridge()
    },
    checkBridge () {
      const version = remoteBridgeVersion()
      if (version) this.setBridgeVersion(version)
    },
    beginUserscriptActivation () {
      this.activationPending = true
      this.activationVersion = remoteBridgeVersion()
    },
    handleActivationReturn () {
      if (!this.activationPending || document.hidden) return
      if (this.activationCheckTimer) window.clearTimeout(this.activationCheckTimer)
      requestRemoteBridgeStatus()
      this.activationCheckTimer = window.setTimeout(() => {
        this.activationCheckTimer = null
        this.checkBridge()
        const versionChanged = remoteBridgeVersion() && remoteBridgeVersion() !== this.activationVersion
        if (versionChanged && isRemoteBridgeInstalled()) {
          this.activationPending = false
          return
        }
        window.location.reload()
      }, 300)
    },
    setInstalled (version) {
      this.setBridgeVersion(version)
    },
    setBridgeVersion (version) {
      this.bridgeVersion = version || remoteBridgeVersion()
      this.bridgeDetected = isRemoteBridgeDetected()
      this.bridgeInstalled = isRemoteBridgeInstalled()
      if (this.bridgeInstalled && this.checkTimer) {
        window.clearInterval(this.checkTimer)
        this.checkTimer = null
      }
    }
  }
}
</script>

<style scoped lang="less">
.remote-bridge-page { max-width: 980px; margin: 0 auto 32px; padding: 0 var(--layout-gutter); }
.bridge-panel { overflow: hidden; }
.bridge-hero { display: flex; align-items: center; justify-content: space-between; gap: 32px; padding: 12px 4px 28px; border-bottom: 1px solid var(--color-border); }
.bridge-copy { max-width: 650px; }
.eyebrow { display: inline-block; margin-bottom: 10px; color: var(--color-text-muted); font-size: 12px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
.bridge-copy h1 { margin: 0 0 12px; color: var(--color-text); font-family: var(--font-serif); font-size: clamp(26px, 4vw, 38px); line-height: 1.15; }
.bridge-copy p { margin: 0; color: var(--color-text-muted); font-size: 15px; line-height: 1.8; }
.bridge-status { display: flex; min-width: 190px; align-items: center; gap: 12px; padding: 14px 16px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg-subtle); }
.bridge-status strong, .bridge-status small { display: block; }
.bridge-status strong { color: var(--color-text); font-size: 14px; }
.bridge-status small { margin-top: 3px; color: var(--color-text-muted); }
.status-dot { width: 10px; height: 10px; flex: none; border-radius: 50%; background: #d69e2e; box-shadow: 0 0 0 4px rgba(214, 158, 46, .13); }
.bridge-status.is-installed .status-dot { background: #2f9e67; box-shadow: 0 0 0 4px rgba(47, 158, 103, .13); }
.bridge-status.is-outdated .status-dot { background: #d97706; box-shadow: 0 0 0 4px rgba(217, 119, 6, .13); }
.install-steps { display: grid; gap: 0; margin: 0; padding: 8px 0 4px; list-style: none; }
.install-steps li { display: grid; grid-template-columns: 42px 1fr; gap: 14px; padding: 24px 4px; border-bottom: 1px solid var(--color-border); }
.install-steps li:last-child { border-bottom: 0; }
.step-number { display: inline-grid; width: 34px; height: 34px; place-items: center; border-radius: 50%; background: var(--color-text); color: var(--color-bg); font-size: 13px; font-weight: 700; }
.install-steps h2 { margin: 2px 0 7px; color: var(--color-text); font-size: 17px; }
.install-steps p { margin: 0 0 14px; color: var(--color-text-muted); font-size: 14px; line-height: 1.7; }
.bridge-button { display: inline-flex; min-height: 38px; align-items: center; justify-content: center; padding: 0 16px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); font-size: 14px; font-weight: 600; text-decoration: none; transition: background var(--transition), border-color var(--transition), color var(--transition); }
.bridge-button.primary { border-color: var(--color-text); background: var(--color-text); color: var(--color-bg); }
.bridge-button.secondary { background: var(--color-bg); color: var(--color-text); }
.bridge-button:hover { border-color: var(--line-strong); background: var(--color-bg-subtle); color: var(--color-text); }
.provider-list { display: flex; flex-wrap: wrap; gap: 8px; }
.provider-list span { padding: 6px 10px; border: 1px solid var(--color-border); border-radius: 9999px; background: var(--color-bg-subtle); color: var(--color-text); font-size: 12px; }
.privacy-note { margin-top: 18px; padding: 16px 18px; border-left: 3px solid var(--color-text); background: var(--color-bg-subtle); color: var(--color-text); }
.privacy-note strong { font-size: 14px; }
.privacy-note p { margin: 5px 0 0; color: var(--color-text-muted); font-size: 13px; line-height: 1.7; }
@media (max-width: 700px) { .bridge-hero { align-items: stretch; flex-direction: column; } .bridge-status { min-width: 0; } }
</style>
