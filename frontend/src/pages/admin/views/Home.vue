<template>
  <div class="container">
    <div>
      <SideMenu></SideMenu>
    </div>
    <div id="header">
      <Icon type="file-text" class="katex-editor" @click="katexVisible=true" />
      <screen-full :width="14" :height="14" class="screen-full"></screen-full>
      <el-dropdown @command="handleCommand">
        <span class="admin-user"><span class="user-avatar">{{ (user.username || '?').slice(0, 1).toUpperCase() }}</span>{{user.username}}<Icon type="arrow-down-b" /></span>
        <template #dropdown><el-dropdown-menu >
          <el-dropdown-item command="logout">Logout</el-dropdown-item>
        </el-dropdown-menu></template>
      </el-dropdown>
    </div>
    <div class="content-app">
      <router-view v-slot="{ Component }">
        <transition name="fadeInUp" mode="out-in">
          <component :is="Component"></component>
        </transition>
      </router-view>
      <div class="footer">
        Powered by XJU-ICTHub · Version 0.2.0
      </div>
    </div>

    <LegacyDialog :title="$t('m.Latex_Editor')" :visible="katexVisible" @update:visible="katexVisible = $event">
      <KatexEditor></KatexEditor>
    </LegacyDialog>
  </div>
</template>
<script>
  import store, { types } from '@/store'
  import { mapGetters } from '@/store/compat'
  import SideMenu from '../components/SideMenu.vue'
  import ScreenFull from '@admin/components/ScreenFull.vue'
  import KatexEditor from '@admin/components/KatexEditor.vue'
  import api from '../api'

  export default {
    name: 'app',
    data () {
      return {
        version: process.env.VERSION,
        katexVisible: false
      }
    },
    components: {
      SideMenu,
      KatexEditor,
      ScreenFull
    },
    async beforeRouteEnter () {
      const res = await api.getProfile()
      if (!res.data.data) return {name: 'login'}
      store.commit(types.CHANGE_PROFILE, {profile: res.data.data})
    },
    methods: {
      handleCommand (command) {
        if (command === 'logout') {
          api.logout().then(() => {
            this.$router.push({name: 'login'})
          })
        }
      }
    },
    computed: {
      ...mapGetters(['user'])
    }
  }
</script>

<style lang="less">
  a {
    background-color: transparent;
  }

  a:active, a:hover {
    outline-width: 0
  }

  img {
    border-style: none
  }

  .container {
    overflow: auto;
    font-weight: 400;
    height: 100%;
    -webkit-font-smoothing: antialiased;
    background-color: var(--color-bg);
    overflow-y: scroll;
    min-width: 760px;
  }

  * {
    box-sizing: border-box;
  }

  #header {
    text-align: right;
    padding-left: 210px;
    padding-right: 30px;
    line-height: 50px;
    height: 50px;
    background: var(--color-bg);
    border-bottom: 1px solid var(--color-border);
    .screen-full {
      margin-right: 8px;
    }
  }

  .content-app {
    padding-top: 20px;
    padding-right: 10px;
    padding-left: 210px;
  }

  .footer {
    margin: 15px;
    text-align: center;
    font-size: small;
  }

  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateY(6px);
    }

    to {
      opacity: 1;
      transform: none;
    }
  }

  .fadeInUp-enter-active {
    animation: fadeInUp 220ms ease both;
  }

  .katex-editor {
    margin-right: 5px;
    cursor: pointer;
  }

  .admin-user { display: inline-flex; align-items: center; gap: 7px; color: var(--color-text); }
  .user-avatar { display: inline-grid; width: 26px; height: 26px; place-items: center; border-radius: 50%; background: var(--color-bg-subtle); font-size: 12px; font-weight: 600; }
  @media (max-width: 760px) { .container { min-width: 0; } #header { padding-left: 180px; padding-right: 14px; } .content-app { padding-left: 180px; } }



</style>
