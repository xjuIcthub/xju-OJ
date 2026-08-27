<template>
  <div class="flex-container">
    <div id="contest-main">
      <!--children-->
      <router-view v-slot="{ Component }">
        <transition name="fadeInUp">
          <component :is="Component"></component>
        </transition>
      </router-view>
      <!--children end-->
      <div class="flex-container" v-if="route_name === 'contest-details'">
        <div id="contest-desc">
          <Panel :padding="20" shadow>
            <template #title><div >
              {{contest.title}}
            </div></template>
            <template #extra><div >
              <Tag type="dot" :color="countdownColor">
                <span id="countdown">{{countdown}}</span>
              </Tag>
            </div></template>
            <div v-html="contest.description" class="markdown-body"></div>
            <div v-if="contestProblemIds.length" class="contest-problem-index">
              <h3>Problems</h3>
              <div class="contest-problem-links">
                <router-link v-for="problemID in contestProblemIds" :key="problemID"
                             :to="{name: 'contest-problem-details', params: {contestID: contestID, problemID: problemID}}">
                  #{{problemID}}
                </router-link>
              </div>
            </div>
            <div v-if="passwordFormVisible" class="contest-password">
              <Input v-model="contestPassword" type="password"
                     placeholder="contest password" class="contest-password-input"
                     @on-enter="checkPassword"/>
              <LegacyButton type="info" @click="checkPassword">Enter</LegacyButton>
            </div>
          </Panel>
          <Table :columns="columns" :data="contest_table" disabled-hover style="margin-bottom: 40px;"></Table>
        </div>
      </div>

    </div>
    <div v-show="showMenu" id="contest-menu">
      <VerticalMenu @on-click="handleRoute">
        <VerticalMenu-item :route="{name: 'contest-details', params: {contestID: contestID}}">
          <Icon type="home"></Icon>
          {{$t('m.Overview')}}
        </VerticalMenu-item>

        <VerticalMenu-item :disabled="contestMenuDisabled"
                           :route="{name: 'contest-announcement-list', params: {contestID: contestID}}">
          <Icon type="chatbubble-working"></Icon>
          {{$t('m.Announcements')}}
        </VerticalMenu-item>

        <VerticalMenu-item :disabled="contestMenuDisabled"
                           :route="{name: 'contest-problem-list', params: {contestID: contestID}}">
          <Icon type="ios-photos"></Icon>
          {{$t('m.Problems')}}
        </VerticalMenu-item>

        <VerticalMenu-item v-if="OIContestRealTimePermission"
                           :disabled="contestMenuDisabled"
                           :route="{name: 'contest-submission-list'}">
          <Icon type="navicon-round"></Icon>
          {{$t('m.Submissions')}}
        </VerticalMenu-item>

        <VerticalMenu-item v-if="OIContestRealTimePermission"
                           :disabled="contestMenuDisabled"
                           :route="{name: 'contest-rank', params: {contestID: contestID}}">
          <Icon type="stats-bars"></Icon>
          {{$t('m.Rankings')}}
        </VerticalMenu-item>

        <VerticalMenu-item v-if="showAdminHelper"
                           :route="{name: 'acm-helper', params: {contestID: contestID}}">
          <Icon type="ios-paw"></Icon>
          {{$t('m.Admin_Helper')}}
        </VerticalMenu-item>
      </VerticalMenu>
    </div>
  </div>
</template>
<script>
  import moment from 'moment'
  import api from '@oj/api'
  import { mapState, mapGetters, mapActions } from '@/store/compat'
  import { types } from '@/store'
  import { CONTEST_STATUS_REVERSE, CONTEST_STATUS } from '@/utils/constants'
  import time from '@/utils/time'

  export default {
    name: 'ContestDetail',
    components: {},
    data () {
      return {
        CONTEST_STATUS: CONTEST_STATUS,
        route_name: '',
        btnLoading: false,
        contestID: '',
        contestPassword: '',
        columns: [
          {
            title: this.$t('m.StartAt'),
            render: (h, params) => {
              return h('span', time.utcToLocal(params.row.start_time))
            }
          },
          {
            title: this.$t('m.EndAt'),
            render: (h, params) => {
              return h('span', time.utcToLocal(params.row.end_time))
            }
          },
          {
            title: this.$t('m.ContestType'),
            render: (h, params) => {
              return h('span', this.$t('m.' + params.row.contest_type ? params.row.contest_type.replace(' ', '_') : ''))
            }
          },
          {
            title: this.$t('m.Rule'),
            render: (h, params) => {
              return h('span', this.$t('m.' + params.row.rule_type))
            }
          },
          {
            title: this.$t('m.Creator'),
            render: (h, data) => {
              return h('span', data.row.created_by.username)
            }
          }
        ]
      }
    },
    mounted () {
      this.contestID = this.$route.params.contestID
      this.route_name = this.$route.name
      this.$store.dispatch('getContest').then(res => {
        this.changeDomTitle({title: res.data.data.title})
        let data = res.data.data
        let endTime = moment(data.end_time)
        if (endTime.isAfter(moment(data.now))) {
          this.timer = setInterval(() => {
            this.$store.commit(types.NOW_ADD_1S)
          }, 1000)
        }
      })
    },
    methods: {
      ...mapActions(['changeDomTitle']),
      handleRoute (route) {
        this.$router.push(route)
      },
      checkPassword () {
        if (this.contestPassword === '') {
          this.$error('Password can\'t be empty')
          return
        }
        this.btnLoading = true
        api.checkContestPassword(this.contestID, this.contestPassword).then((res) => {
          this.$success('Succeeded')
          this.$store.commit(types.CONTEST_ACCESS, {access: true})
          this.btnLoading = false
        }, (res) => {
          this.btnLoading = false
        })
      }
    },
    computed: {
      ...mapState({
        showMenu: state => state.contest.itemVisible.menu,
        contest: state => state.contest.contest,
        contest_table: state => [state.contest.contest],
        now: state => state.contest.now
      }),
      ...mapGetters(
        ['contestMenuDisabled', 'contestRuleType', 'contestStatus', 'countdown', 'isContestAdmin',
          'OIContestRealTimePermission', 'passwordFormVisible']
      ),
      countdownColor () {
        if (this.contestStatus) {
          return CONTEST_STATUS_REVERSE[this.contestStatus].color
        }
      },
      contestProblemIds () {
        return (this.contest.problem_ids || this.contest.problems || []).map(problem => {
          if (typeof problem === 'string' || typeof problem === 'number') return String(problem)
          return problem._id || problem.id || ''
        }).filter(Boolean)
      },
      showAdminHelper () {
        return this.isContestAdmin && this.contestRuleType === 'ACM'
      }
    },
    watch: {
      '$route' (newVal) {
        this.route_name = newVal.name
        this.contestID = newVal.params.contestID
        this.changeDomTitle({title: this.contest.title})
      }
    },
    beforeUnmount () {
      clearInterval(this.timer)
      this.$store.commit(types.CLEAR_CONTEST)
    }
  }
</script>

<style scoped lang="less">
  pre {
    display: inline-block;
  }

  #countdown {
    font-size: 16px;
  }

  .flex-container {
    #contest-main {
      flex: 1 1;
      width: 0;
      #contest-desc {
        flex: auto;
      }
    }
    #contest-menu {
      flex: none;
      width: 210px;
      margin-left: 20px;
    }
    .contest-password {
      margin-top: 20px;
      margin-bottom: -10px;
      &-input {
        width: 200px;
        margin-right: 10px;
      }
    }
    .contest-problem-index {
      margin-top: 24px;
      padding-top: 18px;
      border-top: 1px solid var(--color-border);
      h3 { margin: 0 0 10px; font-size: 16px; font-weight: 600; }
    }
    .contest-problem-links { display: flex; flex-wrap: wrap; gap: 8px; }
    .contest-problem-links a { padding: 6px 10px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-link); background: var(--color-bg); transition: background-color var(--transition), border-color var(--transition); }
    .contest-problem-links a:hover { border-color: var(--line-strong); background: var(--color-bg-subtle); }
  }
</style>
