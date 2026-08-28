<template>
  <div class="home-page">
    <section class="home-columns">
      <div class="home-left-column">
        <div class="home-section">
          <div class="section-heading"><h2>{{ $t('m.Upcoming_Contests') }}</h2><a href="/contest" @click.prevent="go('/contest')">{{ $t('m.View_All') }}</a></div>
          <div v-if="contests.length" class="contest-list">
            <button v-for="contest in contests" :key="contest.id" class="contest-card" @click="goContest(contest)">
              <span class="contest-date">{{ formatContestDate(contest.start_time) }}</span>
              <span class="contest-main"><strong>{{ contest.title }}</strong><small>{{ getDuration(contest.start_time, contest.end_time) }} · {{ contest.rule_type }} · {{ (contest.problem_ids || contest.problems || []).length }} {{ $t('m.Problems') }}</small></span>
              <Icon type="arrow-down-b" class="contest-arrow" />
            </button>
          </div>
          <div v-else class="empty-card">{{ $t('m.No_Upcoming_Contests') }}</div>
        </div>
        <div class="home-section problems-section">
          <div class="section-heading"><h2>{{ $t('m.Problems_Set') }}</h2><a href="/problem" @click.prevent="go('/problem')">{{ $t('m.View_All') }}</a></div>
          <div v-if="problems.length" class="problem-list">
            <button v-for="problem in problems" :key="problem._id" class="problem-card" @click="goProblem(problem)">
              <span class="problem-main"><strong>{{ problem.title }}</strong></span>
            </button>
          </div>
          <div v-else class="empty-card">{{ $t('m.No_Problems_Yet') }}</div>
        </div>
      </div>
      <div class="home-right-column">
        <div class="home-section announcement-section">
          <div class="section-heading"><h2>{{ $t('m.Notice_Board') }}</h2><a href="/faq" @click.prevent="go('/faq')">{{ $t('m.Help_and_FAQ') }}</a></div>
          <div class="announcement-board">
            <div class="notice-board-header"><span class="notice-icon"><Icon type="megaphone" /></span><span><strong>{{ $t('m.Latest_Notices') }}</strong><small>{{ $t('m.Updates_from_XJU_OJ') }}</small></span></div>
            <Announcements />
          </div>
        </div>
        <div class="home-section user-ranking-section">
          <div class="section-heading"><h2>{{ $t('m.User_Ranking') }}</h2></div>
          <div class="ranking-board">
            <button class="ranking-link" @click="go('/acm-rank')">
              <span class="ranking-icon"><Icon type="check-circle" /></span>
              <span><strong>{{ $t('m.Accepted_Count') }} <b v-if="acceptedLeaders.length">{{ acceptedLeaders[0].accepted_number }}</b></strong><small>{{ getLeaderSummary() }}</small></span>
              <Icon type="arrow-down-b" class="ranking-arrow" />
            </button>
            <button class="ranking-link" @click="go('/acm-rank')">
              <span class="ranking-icon"><Icon type="trophy" /></span>
              <span><strong>{{ $t('m.ACM_Rank') }}</strong></span>
              <Icon type="arrow-down-b" class="ranking-arrow" />
            </button>
            <button class="ranking-link" @click="go('/oi-rank')">
              <span class="ranking-icon"><Icon type="stats-bars" /></span>
              <span><strong>{{ $t('m.OI_Rank') }}</strong></span>
              <Icon type="arrow-down-b" class="ranking-arrow" />
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
<script>
import Announcements from './Announcements.vue'
import api from '@oj/api'
import { CONTEST_STATUS, RULE_TYPE } from '@/utils/constants'
import {
  applyDevelopmentContestFixtures,
  applyDevelopmentProblemFixtures,
  cloneFixtures,
  filterMockContests,
  filterMockProblems,
  MOCK_ACM_RANK,
  MOCK_CONTESTS
} from '@oj/mocks/fixtures'

export default {
  name: 'home', components: { Announcements },
  data () {
    return {
      contests: [],
      problems: [],
      acceptedLeaders: cloneFixtures(MOCK_ACM_RANK).slice(0, 3)
    }
  },
  mounted () {
    api.getContestList(0, 5, { status: CONTEST_STATUS.NOT_START }).then(res => {
      const results = (res.data.data && res.data.data.results) || []
      const normalized = applyDevelopmentContestFixtures(results)
      this.contests = normalized.length ? this.withContestProblems(normalized) : cloneFixtures(filterMockContests({ status: CONTEST_STATUS.NOT_START }))
    }).catch(() => { this.contests = cloneFixtures(filterMockContests({ status: CONTEST_STATUS.NOT_START })) })
    api.getProblemList(0, 20, {}).then(res => {
      const results = (res.data.data && res.data.data.results) || []
      const normalized = applyDevelopmentProblemFixtures(results)
      const source = normalized.length ? normalized : filterMockProblems()
      this.problems = source.slice().sort((a, b) => (b.submission_number || 0) - (a.submission_number || 0)).slice(0, 6)
    }).catch(() => { this.problems = cloneFixtures(filterMockProblems()) })
    api.getUserRank(0, 3, RULE_TYPE.ACM).then(res => {
      const results = (res.data.data && res.data.data.results) || []
      if (results.length) this.acceptedLeaders = results
    }).catch(() => {})
  },
  methods: {
    getDuration (startTime, endTime) {
      const hours = Math.abs(new Date(endTime) - new Date(startTime)) / 3600000
      if (hours >= 24) return this.$t('m.Duration_Days', { count: Math.round(hours / 24) })
      return this.$t('m.Duration_Hours', { count: Number(hours.toFixed(1)) })
    },
    formatContestDate (value) {
      return new Intl.DateTimeFormat(this.$i18n.locale, { month: 'short', day: 'numeric' }).format(new Date(value))
    },
    getLeaderSummary () { return this.acceptedLeaders.map(item => `${item.user.username} ${item.accepted_number}`).join(' · ') },
    withContestProblems (contests) {
      return contests.map(contest => {
        const fixture = MOCK_CONTESTS.find(item => String(item.id) === String(contest.id))
        return fixture ? { ...contest, problem_ids: fixture.problem_ids } : contest
      })
    },
    go (path) { this.$router.push(path) },
    goContest (contest) { this.$router.push({ name: 'contest-details', params: { contestID: contest.id } }) },
    goProblem (problem) { this.$router.push({ name: 'problem-details', params: { problemID: problem._id } }) }
  }
}
</script>
<style lang="less" scoped>
.home-page { width: 100%; margin: 0; padding: 30px 0 24px; }
.home-section { padding-top: 30px; }
.section-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; margin-bottom: 14px; }
.section-heading h2 { margin: 0; font: 600 24px/1.2 var(--font-serif); }
.section-heading span { color: var(--color-text-faint); font-size: 13px; }
.section-heading a { color: var(--color-text-muted); font-size: 13px; }
.section-heading a:hover { color: var(--color-link); }
.contest-card, .problem-card { appearance: none; display: flex; align-items: center; width: 100%; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); color: var(--color-text); text-align: left; cursor: pointer; transition: background-color var(--transition), border-color var(--transition), box-shadow var(--transition), transform 180ms ease; }
.contest-card:hover, .problem-card:hover { background: var(--color-bg-subtle); border-color: var(--line-strong); box-shadow: var(--shadow-card); }
.contest-card:active, .problem-card:active { transform: scale(.99); }
.contest-main { display: flex; min-width: 0; flex: 1; flex-direction: column; gap: 3px; }.contest-main strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }.contest-main small { overflow: hidden; color: var(--color-text-muted); text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }.contest-arrow { flex: none; color: var(--color-text-faint); transform: rotate(-90deg); }
.home-columns { display: grid; grid-template-columns: minmax(0, 1fr) minmax(250px, .62fr); gap: 24px; padding-top: 30px; align-items: start; }
.home-left-column { display: grid; gap: 24px; min-width: 0; }
.home-right-column { display: grid; gap: 24px; min-width: 0; }
.home-columns > .home-section, .home-left-column > .home-section, .home-right-column > .home-section { padding-top: 0; }
.contest-list { display: grid; gap: 8px; }.contest-card { padding: 14px 16px; gap: 14px; }.contest-date { display: inline-flex; flex: 0 0 62px; width: 62px; align-items: center; white-space: nowrap; color: var(--cat-competition); font: 600 16px var(--font-serif); }.empty-card { padding: 26px; border: 1px dashed var(--color-border); border-radius: var(--radius-md); color: var(--color-text-faint); text-align: center; }
.problem-list { display: grid; gap: 6px; }.problem-card { appearance: none; display: flex; align-items: center; width: 100%; min-height: 44px; padding: 9px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: var(--color-bg); color: var(--color-text); text-align: left; cursor: pointer; transition: background-color var(--transition), border-color var(--transition), box-shadow var(--transition), transform 180ms ease; }.problem-card:hover { background: var(--color-bg-subtle); border-color: var(--line-strong); box-shadow: var(--shadow-card); }.problem-card:active { transform: scale(.99); }.problem-main { display: flex; min-width: 0; flex: 1; align-items: center; }.problem-main strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
.announcement-board { overflow: hidden; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); }
.notice-board-header { display: flex; align-items: center; gap: 12px; padding: 14px 16px; border-bottom: 1px solid var(--color-border); background: var(--color-bg-subtle); }
.notice-icon { display: grid; width: 32px; height: 32px; place-items: center; border-radius: var(--radius-sm); color: var(--cat-research); background: var(--tag-research-bg); }
.notice-board-header > span:last-child { display: flex; flex-direction: column; gap: 2px; }.notice-board-header strong { font-size: 14px; }.notice-board-header small { color: var(--color-text-muted); font-size: 12px; }
.ranking-board { overflow: hidden; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); }
.ranking-link { appearance: none; display: grid; grid-template-columns: 32px minmax(0, 1fr) 16px; width: 100%; align-items: center; gap: 12px; padding: 13px 14px; border: 0; border-bottom: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text); text-align: left; cursor: pointer; transition: background-color var(--transition); }
.ranking-link:last-child { border-bottom: 0; }.ranking-link:hover { background: var(--color-bg-subtle); }.ranking-link > span:nth-child(2) { display: flex; min-width: 0; flex-direction: column; gap: 2px; }.ranking-link strong { font-size: 14px; }.ranking-link small { color: var(--color-text-muted); font-size: 12px; }
.ranking-link strong b { margin-left: 5px; color: var(--cat-tools); font-size: 12px; font-weight: 600; }
.ranking-icon { display: grid; width: 32px; height: 32px; place-items: center; border-radius: var(--radius-sm); color: var(--cat-tools); background: var(--tag-tools-bg); }.ranking-link:nth-child(2) .ranking-icon { color: var(--cat-competition); background: var(--tag-competition-bg); }.ranking-link:nth-child(3) .ranking-icon { color: var(--cat-kaggle); background: var(--tag-kaggle-bg); }.ranking-arrow { color: var(--color-text-faint); transform: rotate(-90deg); }
.announcement-section :deep(.el-card) { border: 0; border-radius: 0; box-shadow: none; }.announcement-section :deep(.panel-title) { font-size: inherit; }.announcement-section :deep(.el-card__header) { display: none; }.announcement-section :deep(.el-card__body) { padding: 0 16px; }.announcement-section :deep(.announcements-container) { margin: 0; padding: 0; }.announcement-section :deep(.announcements-container li) { margin: 0; padding: 13px 0; border-bottom: 1px solid var(--color-border); }.announcement-section :deep(.announcements-container li:last-child) { border-bottom: 0; }.announcement-section :deep(.flex-container) { align-items: center; }.announcement-section :deep(.creator) { display: none; }.announcement-section :deep(.date) { width: auto; color: var(--color-text-faint); font-size: 12px; }.announcement-section :deep(.title) { padding-left: 0; font-size: 14px; }.announcement-section :deep(.title a.entry) { color: var(--color-text); }.announcement-section :deep(.title a.entry:hover) { color: var(--color-link); }.announcement-section :deep(.no-announcement) { padding: 22px 0; color: var(--color-text-faint); font-size: 13px; }
@media (max-width: 900px) { .home-columns { grid-template-columns: 1fr; gap: 24px; padding-top: 0; } }
@media (max-width: 520px) { .home-page { padding-top: 4px; } }
</style>
