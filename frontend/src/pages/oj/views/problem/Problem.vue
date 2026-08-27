<template>
  <div v-if="problemLoaded" class="flex-container">
    <div id="problem-main">
      <!--problem main-->
      <Panel :padding="40" shadow>
        <template #title><div >{{problem.title}}</div></template>
        <div id="problem-content" class="markdown-body" v-katex>
          <p class="title">{{$t('m.Description')}}</p>
          <p class="content" v-html=problem.description></p>
          <!-- {{$t('m.music')}} -->
          <p class="title">{{$t('m.Input')}} <span v-if="problem.io_mode.io_mode=='File IO'">({{$t('m.FromFile')}}: {{ problem.io_mode.input }})</span></p>
          <p class="content" v-html=problem.input_description></p>

          <p class="title">{{$t('m.Output')}} <span v-if="problem.io_mode.io_mode=='File IO'">({{$t('m.ToFile')}}: {{ problem.io_mode.output }})</span></p>
          <p class="content" v-html=problem.output_description></p>

          <div v-for="(sample, index) of problem.samples" :key="index">
            <div class="flex-container sample">
              <div class="sample-input">
                <p class="title">{{$t('m.Sample_Input')}} {{index + 1}}
                  <a class="copy"
                     role="button"
                     tabindex="0"
                     @click="copySample(sample.input)"
                     @keydown.enter.prevent="copySample(sample.input)">
                    <Icon type="clipboard"></Icon>
                  </a>
                </p>
                <pre>{{sample.input}}</pre>
              </div>
              <div class="sample-output">
                <p class="title">{{$t('m.Sample_Output')}} {{index + 1}}</p>
                <pre>{{sample.output}}</pre>
              </div>
            </div>
          </div>

          <div v-if="problem.hint">
            <p class="title">{{$t('m.Hint')}}</p>
            <Card dis-hover>
              <div class="content" v-html=problem.hint></div>
            </Card>
          </div>

          <div v-if="problem.source">
            <p class="title">{{$t('m.Source')}}</p>
            <p class="content">{{problem.source}}</p>
          </div>

        </div>
      </Panel>
      <!--problem main end-->
      <Card :padding="20" id="submit-code" dis-hover>
        <CodeMirror :value="code" @update:value="code = $event"
                    :languages="problem.languages"
                    :language="language"
                    :theme="theme"
                    @resetCode="onResetToTemplate"
                    @changeTheme="onChangeTheme"
                    @changeLang="onChangeLang"></CodeMirror>
        <Row type="flex" justify="space-between">
          <Col :span="10">
            <div class="status" v-if="statusVisible">
              <template v-if="!this.contestID || (this.contestID && OIContestRealTimePermission)">
                <span>{{$t('m.Status')}}</span>
                <Tag type="dot" :color="submissionStatus.color" @click="handleRoute('/status/'+submissionId)">
                  {{$t('m.' + submissionStatus.text.replace(/ /g, "_"))}}
                </Tag>
              </template>
              <template v-else-if="this.contestID && !OIContestRealTimePermission">
                <Alert type="success" show-icon>{{$t('m.Submitted_successfully')}}</Alert>
              </template>
            </div>
            <div v-else-if="problem.my_status === 0">
              <Alert type="success" show-icon>{{$t('m.You_have_solved_the_problem')}}</Alert>
            </div>
            <div v-else-if="this.contestID && !OIContestRealTimePermission && submissionExists">
              <Alert type="success" show-icon>{{$t('m.You_have_submitted_a_solution')}}</Alert>
            </div>
            <div v-if="contestEnded">
              <Alert type="warning" show-icon>{{$t('m.Contest_has_ended')}}</Alert>
            </div>
          </Col>

          <Col :span="12" class="submit-controls">
            <div v-if="captchaRequired" class="captcha-container">
              <Tooltip :content="$t('m.Click_to_Refresh')" placement="top"><img :src="captchaSrc" @click="getCaptchaSrc"/></Tooltip>
              <Input v-model="captchaCode" class="captcha-code" />
            </div>
            <LegacyButton type="primary" @click="submitCode"
                    :disabled="problemSubmitDisabled || submitted || submitting"
                    :class="['oj-submit-button', { 'is-loading': submitting, 'is-success': submitted }]">
              <Icon v-if="submitting" type="loading" class="submit-spinner" />
              <Icon v-else-if="submitted" type="check" />
              <Icon v-else type="send" />
              <span v-if="submitting">{{$t('m.Submitting')}}</span>
              <span v-else-if="submitted">{{$t('m.Submitted_successfully')}}</span>
              <span v-else>{{$t('m.Submit')}}</span>
            </LegacyButton>
          </Col>
        </Row>
      </Card>
    </div>

    <div id="right-column">
      <section v-if="!this.contestID || OIContestRealTimePermission" class="recent-submission-card" aria-labelledby="recent-submissions-title">
        <button type="button" class="recent-submission-header" @click="handleRoute(submissionRoute)">
          <span id="recent-submissions-title" class="recent-submission-heading">
            <Icon type="navicon-round"></Icon>
            <span>{{$t('m.Submissions')}}</span>
          </span>
          <Icon type="arrow-down-b" class="recent-submission-arrow"></Icon>
        </button>
        <div class="recent-submission-divider"></div>
        <div class="recent-submission-list">
          <div v-for="submission in recentSubmissions" :key="submission.id" class="recent-submission-row">
            <span :class="['submission-status-dot', submissionStatusClass(submission)]"></span>
            <span class="recent-submission-main">
              <strong>{{submission.username}}</strong>
              <small>{{submissionStatusLabel(submission)}} · {{submission.language}}</small>
            </span>
            <time>{{formatSubmissionTime(submission.create_time)}}</time>
          </div>
          <div v-if="!recentSubmissions.length" class="recent-submission-empty">{{ $t('m.No_Recent_Submissions') }}</div>
        </div>
      </section>

      <VerticalMenu v-if="this.contestID" @on-click="handleRoute">
        <template v-if="this.contestID">
          <VerticalMenu-item :route="{name: 'contest-problem-list', params: {contestID: contestID}}">
            <Icon type="ios-photos"></Icon>
            {{$t('m.Problems')}}
          </VerticalMenu-item>

          <VerticalMenu-item :route="{name: 'contest-announcement-list', params: {contestID: contestID}}">
            <Icon type="chatbubble-working"></Icon>
            {{$t('m.Announcements')}}
          </VerticalMenu-item>
        </template>

        <template v-if="this.contestID">
          <VerticalMenu-item v-if="!this.contestID || OIContestRealTimePermission"
                             :route="{name: 'contest-rank', params: {contestID: contestID}}">
            <Icon type="stats-bars"></Icon>
            {{$t('m.Rankings')}}
          </VerticalMenu-item>
          <VerticalMenu-item :route="{name: 'contest-details', params: {contestID: contestID}}">
            <Icon type="home"></Icon>
            {{$t('m.View_Contest')}}
          </VerticalMenu-item>
        </template>
      </VerticalMenu>

      <Card id="info">
        <template #title><div class="info-heading">
          <Icon type="information-circled"></Icon>
          <span class="card-title">{{$t('m.Information')}}</span>
        </div></template>
        <ul>
          <li><span class="info-label">ID</span>
            <span class="info-value">{{problem._id}}</span></li>
          <li>
            <span class="info-label">{{$t('m.Time_Limit')}}</span>
            <span class="info-value">{{problem.time_limit}}MS</span></li>
          <li>
            <span class="info-label">{{$t('m.Memory_Limit')}}</span>
            <span class="info-value">{{problem.memory_limit}}MB</span></li>
          <li>
            <span class="info-label">{{$t('m.IOMode')}}</span>
            <span class="info-value">{{problem.io_mode.io_mode}}</span>
          </li>
          <li>
            <span class="info-label">{{$t('m.Created')}}</span>
            <span class="info-value" :title="problem.created_by.username">{{problem.created_by.username}}</span></li>
          <li v-if="problem.difficulty">
            <span class="info-label">{{$t('m.Level')}}</span>
            <span class="info-value">{{$t('m.' + problem.difficulty)}}</span></li>
          <li v-if="problem.total_score">
            <span class="info-label">{{$t('m.Score')}}</span>
            <span class="info-value">{{problem.total_score}}</span>
          </li>
          <li v-if="problem.spj">
            <span class="info-label">{{ $t('m.Judge') }}</span>
            <span class="info-value">{{ $t('m.Special_Judge') }}</span>
          </li>
          <li>
            <span class="info-label">{{$t('m.Tags')}}</span>
            <span class="info-value">
              <Poptip trigger="hover" placement="left-end">
                <a>{{$t('m.Show')}}</a>
                <template #content><div >
                  <Tag v-for="tag in problem.tags" :key="tag">{{tag}}</Tag>
                </div></template>
              </Poptip>
            </span>
          </li>
        </ul>
      </Card>

      <Card id="pieChart" :padding="0" v-if="!this.contestID || OIContestRealTimePermission">
        <template #title><div >
          <Icon type="ios-analytics"></Icon>
          <span class="card-title">{{$t('m.Statistic')}}</span>
          <LegacyButton type="ghost" size="small" id="detail" @click="graphVisible = !graphVisible">{{ $t('m.Details') }}</LegacyButton>
        </div></template>
        <div class="echarts">
          <ECharts :options="pie"></ECharts>
        </div>
      </Card>
    </div>

    <Modal v-model="graphVisible">
      <div id="pieChart-detail">
        <ECharts :options="largePie" :initOptions="largePieInitOpts"></ECharts>
      </div>
      <template #footer><div >
        <LegacyButton type="ghost" @click="graphVisible=false">{{$t('m.Close')}}</LegacyButton>
      </div></template>
    </Modal>
  </div>
  <div v-else class="problem-loading"><Spin size="large" /></div>
</template>
<script>
  import {mapGetters, mapActions} from '@/store/compat'
  import {types} from '../../../../store'
  import CodeMirror from '@oj/components/CodeMirror.vue'
  import storage from '@/utils/storage'
  import {FormMixin} from '@oj/components/mixins'
  import {JUDGE_STATUS, CONTEST_STATUS, buildProblemCodeKey} from '@/utils/constants'
  import api from '@oj/api'
  import {pie, largePie} from './chartData'
  import { cloneFixtures, MOCK_PROBLEMS, MOCK_SUBMISSIONS } from '@oj/mocks/fixtures'

  // 只显示这些状态的图形占用
  const filtedStatus = ['-1', '-2', '0', '1', '2', '3', '4', '8']

  export default {
    name: 'Problem',
    components: {
      CodeMirror
    },
    mixins: [FormMixin],
    data () {
      return {
        statusVisible: false,
        captchaRequired: false,
        graphVisible: false,
        submissionExists: false,
        captchaCode: '',
        captchaSrc: '',
        contestID: '',
        problemID: '',
        submitting: false,
        code: '',
        language: 'C++',
        theme: 'solarized',
        submissionId: '',
        submitted: false,
        problemLoaded: false,
        recentSubmissions: [],
        result: {
          result: 9
        },
        problem: {
          title: '',
          description: '',
          hint: '',
          my_status: '',
          template: {},
          languages: [],
          created_by: {
            username: ''
          },
          tags: [],
          io_mode: {'io_mode': 'Standard IO'}
        },
        pie: pie,
        largePie: largePie,
        // echarts 无法获取隐藏dom的大小，需手动指定
        largePieInitOpts: {
          width: '500',
          height: '480'
        }
      }
    },
    mounted () {
      const problemCode = storage.get(buildProblemCodeKey(this.$route.params.problemID, this.$route.params.contestID))
      if (problemCode) {
        this.language = problemCode.language
        this.code = problemCode.code
        this.theme = problemCode.theme
      }
      this.$store.commit(types.CHANGE_CONTEST_ITEM_VISIBLE, {menu: false})
      this.init()
    },
    methods: {
      ...mapActions(['changeDomTitle']),
      init () {
        this.$Loading.start()
        this.problemLoaded = false
        this.contestID = this.$route.params.contestID
        this.problemID = this.$route.params.problemID
        let func = this.$route.name === 'problem-details' ? 'getProblem' : 'getContestProblem'
        api[func](this.problemID, this.contestID).then(res => {
          this.applyProblem(res.data.data)
        }).catch(() => {
          const fallback = MOCK_PROBLEMS.find(problem => String(problem._id) === String(this.problemID))
          if (fallback) {
            this.applyProblem(cloneFixtures([fallback])[0])
          } else {
            this.$Loading.error()
          }
        })
      },
      applyProblem (problem) {
        this.$Loading.finish()
        this.changeDomTitle({title: problem.title})
        api.submissionExists(problem.id).then(res => {
          this.submissionExists = res.data.data
        }).catch(() => {
          this.submissionExists = false
        })
        const fixture = MOCK_PROBLEMS.find(item => String(item._id) === String(problem._id))
        if (fixture) {
          // Older API serializers may return template keys with empty values
          // when no PREPEND/TEMPLATE markers are stored. Keep real API fields,
          // but provide the matching local starter code so the editor remains
          // useful in development and theme previews always have code to show.
          const apiTemplates = Object.fromEntries(Object.entries(problem.template || {}).filter(([, value]) => value))
          problem.template = { ...cloneFixtures([fixture])[0].template, ...apiTemplates }
          if (!problem.languages || !problem.languages.length) problem.languages = fixture.languages.slice()
        }
        problem.languages = (problem.languages || []).slice().sort()
        this.problem = problem
        this.loadRecentSubmissions(problem._id)
        if (problem.statistic_info) {
          this.changePie(problem)
        }
        this.problemLoaded = true

        // 在beforeRouteEnter中修改了, 说明本地有code，无需加载template
        if (this.code !== '') {
          return
        }
        // try to load problem template
        this.language = this.problem.languages[0] || 'C++'
        let template = this.problem.template
        if (template && template[this.language]) {
          this.code = template[this.language]
        }
      },
      changePie (problemData) {
        // 只显示特定的一些状态
        for (let k in problemData.statistic_info) {
          if (filtedStatus.indexOf(k) === -1) {
            delete problemData.statistic_info[k]
          }
        }
        let acNum = problemData.accepted_number
        let data = [
          {name: 'WA', value: problemData.submission_number - acNum},
          {name: 'AC', value: acNum}
        ]
        this.pie.series[0].data = data
        // 只把大图的AC selected下，这里需要做一下deepcopy
        let data2 = JSON.parse(JSON.stringify(data))
        data2[1].selected = true
        this.largePie.series[1].data = data2

        // 根据结果设置legend,没有提交过的legend不显示
        let legend = Object.keys(problemData.statistic_info).map(ele => JUDGE_STATUS[ele].short)
        if (legend.length === 0) {
          legend.push('AC', 'WA')
        }
        this.largePie.legend.data = legend

        // 把ac的数据提取出来放在最后
        let acCount = problemData.statistic_info['0']
        delete problemData.statistic_info['0']

        let largePieData = []
        Object.keys(problemData.statistic_info).forEach(ele => {
          largePieData.push({name: JUDGE_STATUS[ele].short, value: problemData.statistic_info[ele]})
        })
        largePieData.push({name: 'AC', value: acCount})
        this.largePie.series[0].data = largePieData
      },
      handleRoute (route) {
        this.$router.push(route)
      },
      onChangeLang (newLang) {
        if (this.problem.template[newLang]) {
          if (this.code.trim() === '') {
            this.code = this.problem.template[newLang]
          }
        }
        this.language = newLang
      },
      onChangeTheme (newTheme) {
        this.theme = newTheme
      },
      loadRecentSubmissions (problemID) {
        const params = { problem_id: problemID }
        const method = this.contestID ? 'getContestSubmissionList' : 'getSubmissionList'
        if (this.contestID) params.contest_id = this.contestID
        api[method](0, 5, params).then(res => {
          const data = res.data.data || {}
          const results = Array.isArray(data.results) ? data.results : []
          this.recentSubmissions = results.length
            ? results.slice().sort((a, b) => new Date(b.create_time) - new Date(a.create_time)).slice(0, 5)
            : this.mockSubmissions(problemID)
        }).catch(() => {
          this.recentSubmissions = this.mockSubmissions(problemID)
        })
      },
      mockSubmissions (problemID) {
        return cloneFixtures(MOCK_SUBMISSIONS.filter(item => String(item.problem) === String(problemID)))
      },
      submissionStatusLabel (submission) {
        const status = JUDGE_STATUS[String(submission.result)] || {}
        return status.short || status.name || 'Pending'
      },
      submissionStatusClass (submission) {
        const status = JUDGE_STATUS[String(submission.result)] || {}
        return `is-${status.type || 'info'}`
      },
      formatSubmissionTime (value) {
        if (!value) return ''
        return this.$filters.localtime(value, 'MMM D HH:mm')
      },
      onResetToTemplate () {
        this.$Modal.confirm({
          content: this.$t('m.Are_you_sure_you_want_to_reset_your_code'),
          onOk: () => {
            let template = this.problem.template
            if (template && template[this.language]) {
              this.code = template[this.language]
            } else {
              this.code = ''
            }
          }
        })
      },
      checkSubmissionStatus () {
        // 使用setTimeout避免一些问题
        if (this.refreshStatus) {
          // 如果之前的提交状态检查还没有停止,则停止,否则将会失去timeout的引用造成无限请求
          clearTimeout(this.refreshStatus)
        }
        const checkStatus = () => {
          let id = this.submissionId
          api.getSubmission(id).then(res => {
            this.result = res.data.data
            if (Object.keys(res.data.data.statistic_info).length !== 0) {
              this.submitting = false
              this.submitted = false
              clearTimeout(this.refreshStatus)
              this.init()
            } else {
              this.refreshStatus = setTimeout(checkStatus, 2000)
            }
          }, res => {
            this.submitting = false
            clearTimeout(this.refreshStatus)
          })
        }
        this.refreshStatus = setTimeout(checkStatus, 2000)
      },
      submitCode () {
        if (this.code.trim() === '') {
          this.$error(this.$t('m.Code_can_not_be_empty'))
          return
        }
        this.submissionId = ''
        this.result = {result: 9}
        this.submitting = true
        let data = {
          problem_id: this.problem.id,
          language: this.language,
          code: this.code,
          contest_id: this.contestID
        }
        if (this.captchaRequired) {
          data.captcha = this.captchaCode
        }
        const submitFunc = (data, detailsVisible) => {
          this.statusVisible = true
          api.submitCode(data).then(res => {
            this.submissionId = res.data.data && res.data.data.submission_id
            // 定时检查状态
            this.submitting = false
            this.submissionExists = true
            if (!detailsVisible) {
              this.$Modal.success({
                title: this.$t('m.Success'),
                content: this.$t('m.Submit_code_successfully')
              })
              return
            }
            this.submitted = true
            this.checkSubmissionStatus()
          }, res => {
            this.getCaptchaSrc()
            if (res.data.data.startsWith('Captcha is required')) {
              this.captchaRequired = true
            }
            this.submitting = false
            this.statusVisible = false
          })
        }

        if (this.contestRuleType === 'OI' && !this.OIContestRealTimePermission) {
          if (this.submissionExists) {
            this.$Modal.confirm({
              title: '',
              content: '<h3>' + this.$t('m.You_have_submission_in_this_problem_sure_to_cover_it') + '<h3>',
              onOk: () => {
                // 暂时解决对话框与后面提示对话框冲突的问题(否则一闪而过）
                setTimeout(() => {
                  submitFunc(data, false)
                }, 1000)
              },
              onCancel: () => {
                this.submitting = false
              }
            })
          } else {
            submitFunc(data, false)
          }
        } else {
          submitFunc(data, true)
        }
      },
      onCopy (event) {
        this.$success('Code copied')
      },
      onCopyError (e) {
        this.$error('Failed to copy code')
      },
      copySample (text) {
        Promise.resolve().then(() => this.$copyText(text)).then(this.onCopy).catch(this.onCopyError)
      }
    },
    computed: {
      ...mapGetters(['problemSubmitDisabled', 'contestRuleType', 'OIContestRealTimePermission', 'contestStatus']),
      contest () {
        return this.$store.state.contest.contest
      },
      contestEnded () {
        return this.contestStatus === CONTEST_STATUS.ENDED
      },
      submissionStatus () {
        return {
          text: JUDGE_STATUS[this.result.result]['name'],
          color: JUDGE_STATUS[this.result.result]['color']
        }
      },
      submissionRoute () {
        if (this.contestID) {
          return {name: 'contest-submission-list', query: {problemID: this.problemID}}
        } else {
          return {name: 'submission-list', query: {problemID: this.problemID}}
        }
      }
    },
    beforeRouteLeave (to, from) {
      // 防止切换组件后仍然不断请求
      clearInterval(this.refreshStatus)

      this.$store.commit(types.CHANGE_CONTEST_ITEM_VISIBLE, {menu: true})
      storage.set(buildProblemCodeKey(this.problem._id, from.params.contestID), {
        code: this.code,
        language: this.language,
        theme: this.theme
      })
    },
    watch: {
      '$route' () {
        this.init()
      }
    }
  }
</script>

<style lang="less" scoped>
  .card-title { margin-left: 0; }
  .info-heading { display: inline-flex; align-items: center; gap: 8px; }

  .flex-container {
    #problem-main {
      flex: auto;
      margin-right: 18px;
    }
    #right-column {
      flex: none;
      width: 220px;
    }
  }

  #problem-content {
    margin-top: -50px;
    .title {
      font-size: 20px;
      font-weight: 400;
      margin: 25px 0 8px 0;
      color: var(--color-link);
      line-height: 28px;
      .copy {
        display: inline-flex;
        width: 22px;
        height: 22px;
        align-items: center;
        justify-content: center;
        margin-left: 5px;
        border-radius: 4px;
        color: var(--color-link);
        vertical-align: middle;
        transition: color var(--transition), background-color var(--transition);
      }
      .copy:hover { background: rgba(35, 131, 226, .08); color: var(--color-link); }
      .copy:focus-visible { outline: 2px solid rgba(35, 131, 226, .32); outline-offset: 1px; color: var(--color-link); }
    }
    :deep(code) {
      border-radius: 4px;
      background: rgba(135, 131, 120, .10);
      color: #c84747;
    }
    :deep(pre) {
      border-radius: var(--radius-sm);
      background: #fcfcfb;
    }
    p.content {
      margin-left: 25px;
      margin-right: 20px;
      font-size: 15px
    }
    .sample {
      align-items: stretch;
      &-input, &-output {
        width: 50%;
        flex: 1 1 auto;
        display: flex;
        flex-direction: column;
        margin-right: 5%;
      }
      pre {
        flex: 1 1 auto;
        align-self: stretch;
        border-style: solid;
        background: transparent;
      }
    }
  }

  #submit-code {
    margin-top: 20px;
    margin-bottom: 20px;
    .status {
      float: left;
      span {
        margin-right: 10px;
        margin-left: 10px;
      }
    }
    .submit-controls { display: flex; align-items: center; justify-content: flex-end; gap: 13px; flex-wrap: wrap; }
    .captcha-container { display: flex; align-items: center; gap: 8px; }
    .captcha-container img { display: block; width: 96px; height: 36px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); cursor: pointer; }
    .captcha-code { width: 120px; }
    .oj-submit-button { min-width: 132px; min-height: 40px; border-radius: var(--radius-md); gap: 7px; font-weight: 600; }
    :deep(.oj-submit-button > span) { display: inline-flex; align-items: center; justify-content: center; gap: 10px; white-space: nowrap; }
    :deep(.oj-submit-button .legacy-icon) { display: inline-flex; flex: none; align-items: center; }
    .oj-submit-button.is-success { background: var(--oj-success); border-color: var(--oj-success); color: #fff; }
    .oj-submit-button.is-loading { cursor: wait; }
    .submit-spinner { animation: oj-submit-spin 900ms linear infinite; }
    @keyframes oj-submit-spin { to { transform: rotate(360deg); } }
  }

  .recent-submission-card {
    overflow: hidden;
    margin-bottom: 20px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    box-shadow: var(--shadow-card);
  }
  .recent-submission-header {
    display: flex;
    width: 100%;
    min-height: 52px;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border: 0;
    background: var(--color-bg);
    color: var(--color-text-muted);
    text-align: left;
    cursor: pointer;
    transition: color var(--transition), background-color var(--transition);
  }
  .recent-submission-header:hover, .recent-submission-header:focus-visible { background: var(--color-bg); color: var(--color-text-muted); }
  .recent-submission-heading { display: inline-flex; align-items: center; gap: 8px; font-size: 14px; }
  .recent-submission-heading :deep(.legacy-icon) { display: inline-flex; align-items: center; }
  .recent-submission-arrow { color: var(--color-text-faint); transform: rotate(-90deg); }
  .recent-submission-divider { width: 34px; height: 1px; margin: 0 16px 4px; background: var(--line-strong); }
  .recent-submission-list { padding: 2px 16px 8px; }
  .recent-submission-row { display: flex; min-width: 0; align-items: center; gap: 8px; padding: 9px 0; border-bottom: 1px solid var(--color-border); }
  .recent-submission-row:last-child { border-bottom: 0; }
  .submission-status-dot { width: 7px; height: 7px; flex: none; border-radius: 50%; background: var(--color-text-faint); }
  .submission-status-dot.is-success { background: var(--oj-success); }
  .submission-status-dot.is-error { background: var(--oj-danger); }
  .submission-status-dot.is-warning { background: var(--oj-warning); }
  .submission-status-dot.is-info { background: var(--oj-info); }
  .recent-submission-main { display: flex; min-width: 0; flex: 1; flex-direction: column; gap: 1px; }
  .recent-submission-main strong { overflow: hidden; color: var(--color-text); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
  .recent-submission-main small, .recent-submission-row time { color: var(--color-text-muted); font-size: 11px; white-space: nowrap; }
  .recent-submission-row time { flex: none; color: var(--color-text-faint); }
  .recent-submission-empty { padding: 14px 0 10px; color: var(--color-text-faint); font-size: 12px; }

  #info {
    margin-bottom: 20px;
    margin-top: 20px;
    ul { list-style-type: none; margin: 0; padding: 0; }
    li {
      display: flex;
      min-height: 36px;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      margin: 0;
      padding: 8px 0;
      border-bottom: 1px dotted var(--color-border);
    }
    li:last-child { border-bottom: 0; }
    .info-label { flex: 0 0 auto; color: var(--color-text); font-weight: 600; }
    .info-value { min-width: 0; overflow: hidden; color: var(--color-text-muted); text-align: right; text-overflow: ellipsis; white-space: nowrap; }
    .info-value :deep(a) { color: var(--color-link); }
  }

  #right-column > :deep(.el-card) { margin-bottom: 20px; }

  @media (max-width: 760px) { #submit-code .submit-controls { justify-content: stretch; } #submit-code .oj-submit-button { flex: 1 1 100%; } #submit-code .captcha-container { flex: 1 1 100%; } #submit-code .captcha-code { flex: 1; width: auto; } }

  #pieChart {
    .echarts {
      height: 250px;
      width: 210px;
    }
    #detail {
      position: absolute;
      right: 10px;
      top: 10px;
    }
  }

  #pieChart-detail {
    margin-top: 20px;
    width: 500px;
    height: 480px;
  }

  @media (max-width: 900px) {
    .flex-container { flex-direction: column; }
    .flex-container #problem-main { width: 100%; margin-right: 0; }
    .flex-container #right-column { width: 100%; }
    #info, #pieChart { width: 100%; }
    .recent-submission-card { width: 100%; }
  }
</style>
