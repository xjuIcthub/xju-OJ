<template>
  <div class="login-container">
    <div class="brand-mark">XJ</div>
    <h3 class="title">{{$t('m.Welcome_to_Login')}}</h3>
    <p v-if="authentikEnabled" class="auth-copy">{{$t('m.Authentik_Account_Notice')}}</p>
    <el-button v-if="authentikEnabled" type="primary" class="auth-button" @click="startAuthentikLogin">
      {{$t('m.Login_with_Authentik')}}
    </el-button>
    <div v-if="authentikEnabled && localLoginEnabled" class="auth-divider"><span>or</span></div>
    <el-form v-if="localLoginEnabled" :model="ruleForm2" :rules="rules2" ref="ruleForm2" label-position="left" label-width="0px"
             class="local-login-form">
      <el-form-item prop="account">
        <el-input type="text" v-model="ruleForm2.account" auto-complete="off" :placeholder="$t('m.username')" @keyup.enter="handleLogin"></el-input>
      </el-form-item>
      <el-form-item prop="password">
        <el-input type="password" v-model="ruleForm2.password" auto-complete="off" :placeholder="$t('m.password')" @keyup.enter="handleLogin"></el-input>
      </el-form-item>
      <el-form-item style="width:100%;">
        <el-button type="primary" style="width:100%;" @click.prevent="handleLogin" :loading="logining">{{$t('m.GO')}}
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script>
  import api from '../../api'
  import runtime from '@/utils/runtime'

  export default {
    data () {
      return {
        logining: false,
        ruleForm2: {
          account: '',
          password: ''
        },
        rules2: {
          account: [
            {required: true, trigger: 'blur'}
          ],
          password: [
            {required: true, trigger: 'blur'}
          ]
        },
        checked: true
      }
    },
    computed: {
      authentikEnabled () {
        return runtime.AUTHENTIK_OIDC_ENABLED
      },
      localLoginEnabled () {
        return runtime.AUTHENTIK_LOCAL_LOGIN_ENABLED !== false
      }
    },
    methods: {
      startAuthentikLogin () {
        const url = new URL('/api/auth/oidc/login/', window.location.origin)
        url.searchParams.set('next', '/admin/')
        window.location.assign(url.toString())
      },
      handleLogin (ev) {
        this.$refs.ruleForm2.validate((valid) => {
          if (valid) {
            this.logining = true
            api.login(this.ruleForm2.account, this.ruleForm2.password).then(data => {
              this.logining = false
              this.$router.push({name: 'dashboard'})
            }, () => {
              this.logining = false
            })
          } else {
            this.$error('Please check the error fields')
          }
        })
      }
    }
  }
</script>

<style lang="less" scoped>
  .login-container {
    margin: 140px auto;
    width: min(390px, calc(100% - 32px));
    padding: 36px;
    border: 1px solid var(--oj-border);
    border-radius: var(--radius-lg);
    background: var(--oj-surface);
    box-shadow: var(--oj-shadow-card);
    .brand-mark {
      display: grid;
      width: 42px;
      height: 42px;
      margin: 0 auto 18px;
      place-items: center;
      border-radius: var(--radius-lg);
      background: var(--oj-accent);
      color: #fffdf9;
      font-size: 13px;
      font-weight: 800;
      letter-spacing: .08em;
    }
    .title {
      margin: 0 auto 12px;
      text-align: center;
      color: var(--oj-text);
    }
    .auth-copy {
      margin: 0 0 18px;
      color: var(--oj-text-muted);
      text-align: center;
      line-height: 1.6;
    }
    .auth-button {
      width: 100%;
      height: 42px;
    }
    .auth-divider {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 20px 0;
      color: var(--oj-text-faint);
      font-size: 12px;
      text-align: center;
    }
    .auth-divider::before,
    .auth-divider::after {
      content: '';
      height: 1px;
      flex: 1;
      background: var(--oj-border);
    }
    .local-login-form {
      :deep(.el-form-item:last-child) {
        margin-bottom: 0;
      }
    }
  }
</style>
