<template>
  <div id="header">
    <Menu theme="light" mode="horizontal" @on-select="handleRoute" :active-name="activeMenu" class="oj-menu">
      <div class="logo">
        <span class="brand-mark">OJ</span>
        <span class="brand-name">{{website.website_name}}</span>
      </div>
      <Menu-item name="/">
        <Icon type="home"></Icon>
        {{$t('m.Home')}}
      </Menu-item>
      <Menu-item name="/problem">
        <Icon type="ios-keypad"></Icon>
        {{$t('m.NavProblems')}}
      </Menu-item>
      <Menu-item name="/contest">
        <Icon type="trophy"></Icon>
        {{$t('m.Contests')}}
      </Menu-item>
      <Menu-item name="/status">
        <Icon type="ios-pulse-strong"></Icon>
        {{$t('m.NavStatus')}}
      </Menu-item>
      <Submenu name="rank">
        <template #title>
          <Icon type="podium"></Icon>
          {{$t('m.Rank')}}
        </template>
        <Menu-item name="/acm-rank">
          {{$t('m.ACM_Rank')}}
        </Menu-item>
        <Menu-item name="/oi-rank">
          {{$t('m.OI_Rank')}}
        </Menu-item>
      </Submenu>
      <Submenu name="about">
        <template #title>
          <Icon type="information-circled"></Icon>
          {{$t('m.About')}}
        </template>
        <Menu-item name="/about">
          {{$t('m.Judger')}}
        </Menu-item>
        <Menu-item name="/FAQ">
          {{$t('m.FAQ')}}
        </Menu-item>
      </Submenu>
      <template v-if="!isAuthenticated">
        <div class="btn-menu">
          <LegacyButton type="ghost"
                  ref="loginBtn"
                  shape="circle"
                  @click="handleBtnClick('login')">{{$t('m.Login')}}
          </LegacyButton>
          <LegacyButton v-if="website.allow_register && authentikEnabled"
                  type="ghost"
                  shape="circle"
                  @click="goAuthentikRegister"
                  style="margin-left: 5px;">{{$t('m.Register')}}
          </LegacyButton>
          <LegacyButton v-else-if="website.allow_register && localRegisterEnabled"
                  type="ghost"
                  shape="circle"
                  @click="handleBtnClick('register')"
                  style="margin-left: 5px;">{{$t('m.Register')}}
          </LegacyButton>
        </div>
      </template>
      <template v-else>
        <Dropdown class="drop-menu" @on-click="handleRoute" placement="bottom" trigger="click">
          <LegacyButton type="text" class="drop-menu-title">{{ user.username }}
            <Icon type="arrow-down-b"></Icon>
          </LegacyButton>
          <template #list><Dropdown-menu >
            <Dropdown-item name="/user-home">{{$t('m.MyHome')}}</Dropdown-item>
            <Dropdown-item name="/status?myself=1">{{$t('m.MySubmissions')}}</Dropdown-item>
            <Dropdown-item name="/setting/profile">{{$t('m.Settings')}}</Dropdown-item>
            <Dropdown-item v-if="isAdminRole" name="/admin">{{$t('m.Management')}}</Dropdown-item>
            <Dropdown-item divided name="/logout">{{$t('m.Logout')}}</Dropdown-item>
          </Dropdown-menu></template>
        </Dropdown>
      </template>
    </Menu>
    <Modal v-model="modalVisible" :width="400">
      <template #header><div  class="modal-title">{{$t('m.Welcome_to')}} {{website.website_name_shortcut}}</div></template>
      <component :is="modalStatus.mode" v-if="modalVisible"></component>
      <template #footer><div  style="display: none"></div></template>
    </Modal>
  </div>
</template>
<script>
  import { mapGetters, mapActions } from '@/store/compat'
  import login from '@oj/views/user/Login'
  import register from '@oj/views/user/Register'

  export default {
    components: {
      login,
      register
    },
    mounted () {
      this.getProfile()
    },
    methods: {
      ...mapActions(['getProfile', 'changeModalStatus']),
      handleRoute (route) {
        if (route && route.indexOf('admin') < 0) {
          this.$router.push(route)
        } else {
          window.open('/admin/')
        }
      },
      handleBtnClick (mode) {
        this.changeModalStatus({
          visible: true,
          mode: mode
        })
      },
      goAuthentikRegister () {
        const url = this.authProviders.authentik && this.authProviders.authentik.register_url
        if (url) window.location.assign(url)
      }
    },
    computed: {
      ...mapGetters(['website', 'modalStatus', 'user', 'isAuthenticated', 'isAdminRole', 'authProviders']),
      authentikEnabled () {
        return !!(this.authProviders.authentik && this.authProviders.authentik.enabled)
      },
      localRegisterEnabled () {
        return !this.authProviders.local || this.authProviders.local.register_enabled !== false
      },
      // 跟随路由变化
      activeMenu () {
        return '/' + this.$route.path.split('/')[1]
      },
      modalVisible: {
        get () {
          return this.modalStatus.visible
        },
        set (value) {
          this.changeModalStatus({visible: value})
        }
      }
    }
  }
</script>

<style lang="less" scoped>
  #header {
    min-width: 300px;
    position: fixed;
    top: 0;
    left: 0;
    height: auto;
    width: 100%;
    z-index: 1000;
    background-color: #fff;
    box-shadow: 0 1px 5px 0 rgba(0, 0, 0, 0.1);
    .oj-menu {
      min-height: 64px;
      border-bottom: 0;
      background: rgb(255 253 249 / 88%);
      backdrop-filter: blur(18px);
    }

    .logo {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      margin: 0 22px 0 2%;
      font-size: 18px;
      font-weight: 700;
      line-height: 64px;
      color: var(--oj-text);
      white-space: nowrap;
      .brand-mark {
        display: inline-grid;
        width: 34px;
        height: 34px;
        place-items: center;
        border-radius: 11px;
        background: var(--oj-accent);
        color: #fffdf9;
        font-size: 12px;
        letter-spacing: .08em;
        line-height: 1;
      }
      .brand-name {
        max-width: 180px;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }

    .drop-menu {
      float: right;
      margin-right: 30px;
      position: absolute;
      right: 10px;
      &-title {
        font-size: 16px;
        color: var(--oj-text);
      }
    }
    .btn-menu {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 16px;
      float: right;
      margin-right: 16px;
    }
  }

  @media screen and (max-width: 760px) {
    #header {
      .oj-menu {
        overflow-x: auto;
      }
      .logo {
        margin-left: 14px;
        margin-right: 10px;
        .brand-name {
          display: none;
        }
      }
      .btn-menu {
        margin-right: 8px;
      }
    }
  }

  .modal {
    &-title {
      font-size: 18px;
      font-weight: 600;
    }
  }
</style>
