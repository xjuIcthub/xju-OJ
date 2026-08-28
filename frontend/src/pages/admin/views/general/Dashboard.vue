<template>
  <el-row type="flex" :gutter="20">
    <el-col :md="10" :lg="8">
      <el-card class="admin-info">
        <el-row :gutter="20">
          <el-col :span="10">
            <UserAvatar class="avatar" :src="profile.avatar" :username="user.username" :size="92" />
          </el-col>
          <el-col :span="14">
            <p class="admin-info-name">{{user.username}}</p>
            <p>{{user.admin_type}}</p>
          </el-col>
        </el-row>
        <hr/>
        <div class="last-info">
          <p class="last-info-title">{{$t('m.Last_Login')}}</p>
          <el-form label-width="80px" class="last-info-body">
            <el-form-item label="Time:">
              <span>{{ $filters.localtime(session.last_activity) }}</span>
            </el-form-item>
            <el-form-item label="IP:">
              <span>{{session.ip}}</span>
            </el-form-item>
            <el-form-item label="OS">
              <span>{{os}}</span>
            </el-form-item>
            <el-form-item label="Browser:">
              <span>{{browser}}</span>
            </el-form-item>
          </el-form>
        </div>
      </el-card>
      <panel :title="$t('m.System_Overview')" v-if="isSuperAdmin">
        <p>{{$t('m.DashBoardJudge_Server')}}:  {{infoData.judge_server_count}}</p>
        <p>{{$t('m.HTTPS_Status')}}:
          <el-tag :type="https ? 'success' : 'danger'" size="small">
            {{ https ? 'Enabled' : 'Disabled'}}
          </el-tag>
        </p>
        <p>{{$t('m.Force_HTTPS')}}:
          <el-tag :type="forceHttps ? 'success' : 'danger'" size="small">
            {{forceHttps ? 'Enabled' : 'Disabled'}}
          </el-tag>
        </p>
        <p>{{$t('m.CDN_HOST')}}:
          <el-tag :type="cdn ? 'success' : 'warning'" size="small">
            {{cdn ? cdn : 'Not Use'}}
          </el-tag>
        </p>
      </panel>
    </el-col>

    <el-col :md="14" :lg="16" v-if="isSuperAdmin">
      <div class="info-container">
        <info-card color="#78736a" icon="users" message="Total Users" iconSize="30px" class="info-item"
                   :value="infoData.user_count"></info-card>
        <info-card color="#0f7b6c" icon="bars" message="Today Submissions" class="info-item"
                   :value="infoData.today_submission_count"></info-card>
        <info-card color="#b7791f" icon="trophy" message="Recent Contests" class="info-item"
                   :value="infoData.recent_contest_count"></info-card>
      </div>
      <panel style="margin-top: 5px">
        <template #title><span>XJU-OJ Release Notes</span></template>

        <el-collapse v-model="activeNames" v-for="(release, index) of releases" :key="'release' + index">
          <el-collapse-item :name="index+1">
            <template #title>
              <div v-if="release.current">{{release.title}}
                <el-tag size="small" type="success">Current</el-tag>
              </div>
              <span v-else>{{release.title}}</span>
            </template>
            <p class="release-meta">{{release.date}} · {{release.level}}</p>
            <div class="release-body"><ul><li v-for="detail in release.details" :key="detail">{{detail}}</li></ul></div>
          </el-collapse-item>
        </el-collapse>
      </panel>
    </el-col>
  </el-row>
</template>
<script>
  import { mapGetters } from '@/store/compat'
  import browserDetector from 'browser-detect'
  import InfoCard from '@admin/components/infoCard.vue'
  import api from '@admin/api'
  import UserAvatar from '@/shared/ui/UserAvatar.vue'

  export default {
    name: 'dashboard',
    components: {
      InfoCard,
      UserAvatar
    },
    data () {
      return {
        infoData: {
          user_count: 0,
          recent_contest_count: 0,
          today_submission_count: 0,
          judge_server_count: 0,
          env: {}
        },
        activeNames: [1],
        session: {},
        releases: [
          {
            title: 'Version 0.2.0 · Feiyue visual migration',
            date: '2026-08',
            level: 'Current stable iteration',
            current: true,
            details: [
              'Unified the public OJ and admin console with the XJU-Feiyue design system.',
              'Added Lucide icon compatibility, responsive navigation, refined tables, dialogs and submission states.',
              'Modernized the Vue 3, Element Plus, Vite and local frontend development workflow.'
            ]
          },
          {
            title: 'Version 0.1.0 · XJU-OJ platform modernization',
            date: '2026-07',
            level: 'Foundation iteration',
            current: false,
            details: [
              'Upgraded the application runtime, deployment pipeline and dual-entry frontend build.',
              'Introduced Authentik integration, stricter CSRF boundaries and reproducible container builds.',
              'Preserved the existing judge, contest, submission and editor behavior during migration.'
            ]
          }
        ]
      }
    },
    mounted () {
      api.getDashboardInfo().then(resp => {
        this.infoData = resp.data.data
      }, () => {
      })
      api.getSessions().then(resp => {
        this.parseSession(resp.data.data)
      }, () => {
      })
    },
    methods: {
      parseSession (sessions) {
        let session = sessions[0]
        if (sessions.length > 1) {
          session = sessions.filter(s => !s.current_session).sort((a, b) => {
            return a.last_activity < b.last_activity
          })[0]
        }
        this.session = session
      }
    },
    computed: {
      ...mapGetters(['profile', 'user', 'isSuperAdmin']),
      cdn () {
        return this.infoData.env.STATIC_CDN_HOST
      },
      https () {
        return document.URL.slice(0, 5) === 'https'
      },
      forceHttps () {
        return this.infoData.env.FORCE_HTTPS
      },
      browser () {
        let b = browserDetector(this.session.user_agent)
        if (b.name && b.version) {
          return b.name + ' ' + b.version
        } else {
          return 'Unknown'
        }
      },
      os () {
        let b = browserDetector(this.session.user_agent)
        return b.os ? b.os : 'Unknown'
      }
    }
  }
</script>

<style lang="less">
  .admin-info {
    margin-bottom: 20px;
    &-name {
      font-size: 24px;
      font-weight: 700;
      margin-bottom: 10px;
      color: #409EFF;
    }
    .avatar {
      max-width: 100%;
    }
    .avatar-fallback {
      display: grid;
      width: 92px;
      height: 92px;
      place-items: center;
      border-radius: 50%;
      background: var(--color-bg-subtle);
      color: var(--color-text);
      font-size: 30px;
      font-weight: 700;
    }
    .last-info {
      &-title {
        font-size: 16px;
      }
      &-body {
        .el-form-item {
          margin-bottom: 5px;
        }
      }
    }
  }

  .info-container {
    display: flex;
    justify-content: flex-start;
    flex-wrap: wrap;
    .info-item {
      flex: 1 0 auto;
      min-width: 200px;
      margin-bottom: 10px;
    }
  }

  .release-meta {
    margin: 4px 0 8px;
    color: var(--color-text-faint);
    font-size: 12px;
  }

  .release-body ul {
    margin: 6px 0;
    padding-left: 20px;
  }

</style>
