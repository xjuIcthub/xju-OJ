<template>
  <div class="view">
    <Panel :title="$t('m.SMTP_Config')">
      <el-form label-position="left" label-width="70px" :model="smtp">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('m.Server')" required>
              <el-input v-model="smtp.server" placeholder="SMTP 服务器地址"></el-input>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('m.Port')" required>
              <el-input type="number" v-model="smtp.port" placeholder="SMTP 服务器端口"></el-input>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('m.Email')" required>
              <el-input v-model="smtp.email" placeholder="用于发送邮件的账号"></el-input>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('m.Password')" label-width="90px" required>
              <el-input v-model="smtp.password" type="password" placeholder="SMTP 服务器授权码"></el-input>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="TLS">
              <el-switch
                v-model="smtp.tls">
              </el-switch>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <el-button type="primary" @click="saveSMTPConfig">保存</el-button>
      <el-button type="warning" @click="testSMTPConfig"
                 v-if="saved" :loading="loadingBtnTest">发送测试邮件</el-button>
    </Panel>

    <Panel :title="$t('m.Website_Config')">
      <el-form label-position="left" label-width="100px" ref="form" :model="websiteConfig">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item :label="$t('m.Base_Url')" required>
              <el-input v-model="websiteConfig.website_base_url" placeholder="网站基础地址"></el-input>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="$t('m.Name')" required>
              <el-input v-model="websiteConfig.website_name" placeholder="网站名称"></el-input>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="$t('m.Shortcut')" required>
              <el-input v-model="websiteConfig.website_name_shortcut" placeholder="网站简称"></el-input>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item :label="$t('m.Footer')" required>
              <el-input type="textarea" :autosize="{ minRows: 2, maxRows: 4}" v-model="websiteConfig.website_footer"
                        placeholder="网站页脚 HTML"></el-input>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-col :span="12">
              <el-form-item :label="$t('m.Allow_Register')" label-width="200px">
                <el-switch
                  v-model="websiteConfig.allow_register"
                  active-color="#13ce66"
                  inactive-color="#ff4949">
                </el-switch>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="$t('m.Submission_List_Show_All')" label-width="200px">
                <el-switch
                  v-model="websiteConfig.submission_list_show_all"
                  active-color="#13ce66"
                  inactive-color="#ff4949">
                </el-switch>
              </el-form-item>
            </el-col>
          </el-col>
        </el-row>
      </el-form>
      <save @click="saveWebsiteConfig"></save>
    </Panel>
  </div>
</template>

<script>
  import api from '../../api.js'

  export default {
    name: 'Conf',
    data () {
      return {
        init: false,
        saved: false,
        loadingBtnTest: false,
        smtp: {
          server: 'smtp.example.com',
          port: 25,
          password: '',
          email: 'email@example.com',
          tls: true
        },
        websiteConfig: {}
      }
    },
    mounted () {
      api.getSMTPConfig().then(res => {
        if (res.data.data) {
          this.smtp = res.data.data
        } else {
          this.init = true
          this.$warning('请先配置 SMTP')
        }
      })
      api.getWebsiteConfig().then(res => {
        this.websiteConfig = res.data.data
      }).catch(() => {
      })
    },
    methods: {
      saveSMTPConfig () {
        if (!this.init) {
          api.editSMTPConfig(this.smtp).then(() => {
            this.saved = true
          }, () => {
          })
        } else {
          api.createSMTPConfig(this.smtp).then(() => {
            this.saved = true
          }, () => {
          })
        }
      },
      testSMTPConfig () {
        this.$prompt('请输入接收测试邮件的邮箱', '测试 SMTP', {
          inputPattern: /[\w!#$%&'*+/=?^_`{|}~-]+(?:\.[\w!#$%&'*+/=?^_`{|}~-]+)*@(?:[\w](?:[\w-]*[\w])?\.)+[\w](?:[\w-]*[\w])?/,
          inputErrorMessage: '邮箱格式不正确'
        }).then(({value}) => {
          this.loadingBtnTest = true
          api.testSMTPConfig(value).then(() => {
            this.loadingBtnTest = false
          }, () => {
            this.loadingBtnTest = false
          })
        }).catch(() => {
        })
      },
      saveWebsiteConfig () {
        api.editWebsiteConfig(this.websiteConfig).then(() => {
        }).catch(() => {
        })
      }
    }
  }
</script>
