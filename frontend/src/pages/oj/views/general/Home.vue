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
          <div v-if="problems.length" class="problem-table-shell">
            <table class="home-problem-table">
              <tbody>
                <tr v-for="problem in problems" :key="problem._id">
                  <td class="problem-id-cell">
                    <button type="button" class="problem-table-link problem-display-id" @click="goProblem(problem)">{{ problem._id }}</button>
                  </td>
                  <td class="problem-title-cell">
                    <button type="button" class="problem-table-link problem-table-title" @click="goProblem(problem)">{{ problem.title }}</button>
                  </td>
                  <td>
                    <span v-if="problem.difficulty"
                          :class="['home-difficulty-badge', `difficulty-${problem.difficulty.toLowerCase()}`]">
                      {{ difficultyLabel(problem.difficulty) }}
                    </span>
                    <span v-else class="table-empty-value">—</span>
                  </td>
                  <td>
                    <div v-if="problemTags(problem).length" class="home-problem-tags">
                      <span v-for="(tag, index) in problemTags(problem)" :key="`${tag}-${index}`">{{ tag }}</span>
                    </div>
                    <span v-else class="table-empty-value">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
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
          <div class="section-heading ranking-heading">
            <h2>{{ $t('m.User_Ranking') }}</h2>
            <div :class="['ranking-tabs', {'is-oi': rankingMode === 'OI'}]" role="tablist" :aria-label="$t('m.User_Ranking')">
              <button type="button"
                      role="tab"
                      :aria-selected="rankingMode === 'ACM'"
                      @click="rankingMode = 'ACM'">{{ $t('m.ACM_Rank') }}</button>
              <button type="button"
                      role="tab"
                      :aria-selected="rankingMode === 'OI'"
                      @click="rankingMode = 'OI'">{{ $t('m.OI_Rank') }}</button>
            </div>
          </div>
          <div class="ranking-board">
            <table class="home-ranking-table">
              <thead>
                <tr><th scope="col">{{ $t('m.Rank') }}</th><th scope="col">{{ $t('m.Username') }}</th></tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in rankingRows" :key="`${rankingMode}-${rankingUsername(row)}-${index}`">
                  <td>{{ index + 1 }}</td>
                  <td>
                    <button type="button" class="ranking-username" @click="goUser(rankingUsername(row))">{{ rankingUsername(row) }}</button>
                  </td>
                </tr>
              </tbody>
            </table>
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
  MOCK_CONTESTS,
  MOCK_OI_RANK
} from '@oj/mocks/fixtures'

const problemIdCollator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' })

export default {
  name: 'home', components: { Announcements },
  data () {
    return {
      contests: [],
      problems: [],
      rankingMode: RULE_TYPE.ACM,
      rankings: {
        [RULE_TYPE.ACM]: cloneFixtures(MOCK_ACM_RANK).slice(0, 5),
        [RULE_TYPE.OI]: cloneFixtures(MOCK_OI_RANK).slice(0, 5)
      }
    }
  },
  mounted () {
    api.getContestList(0, 5, { status: CONTEST_STATUS.NOT_START }).then(res => {
      const results = (res.data.data && res.data.data.results) || []
      const normalized = applyDevelopmentContestFixtures(results)
      this.contests = normalized.length ? this.withContestProblems(normalized) : cloneFixtures(filterMockContests({ status: CONTEST_STATUS.NOT_START }))
    }).catch(() => { this.contests = cloneFixtures(filterMockContests({ status: CONTEST_STATUS.NOT_START })) })
    this.loadLatestProblems()
    this.loadRanking(RULE_TYPE.ACM, MOCK_ACM_RANK)
    this.loadRanking(RULE_TYPE.OI, MOCK_OI_RANK)
  },
  methods: {
    difficultyLabel (difficulty) {
      return this.$t('m.Difficulty_' + difficulty)
    },
    getDuration (startTime, endTime) {
      const hours = Math.abs(new Date(endTime) - new Date(startTime)) / 3600000
      if (hours >= 24) return this.$t('m.Duration_Days', { count: Math.round(hours / 24) })
      return this.$t('m.Duration_Hours', { count: Number(hours.toFixed(1)) })
    },
    formatContestDate (value) {
      return new Intl.DateTimeFormat(this.$i18n.locale, { month: 'short', day: 'numeric' }).format(new Date(value))
    },
    loadLatestProblems () {
      const batchSize = 20
      api.getProblemList(0, batchSize, {}).then(res => {
        const payload = res.data.data || {}
        const total = Number(payload.total) || (payload.results || []).length
        if (total > batchSize) {
          return api.getProblemList(Math.max(0, total - batchSize), batchSize, {}).then(latestRes => {
            this.setHomeProblems((latestRes.data.data && latestRes.data.data.results) || [])
          }).catch(() => { this.setHomeProblems(payload.results || []) })
        }
        this.setHomeProblems(payload.results || [])
      }).catch(() => { this.setHomeProblems(cloneFixtures(filterMockProblems())) })
    },
    setHomeProblems (results) {
      const normalized = applyDevelopmentProblemFixtures(results)
      const source = normalized.length ? normalized : cloneFixtures(filterMockProblems())
      this.problems = source.slice().sort((a, b) => problemIdCollator.compare(String(b._id), String(a._id))).slice(0, 6)
    },
    problemTags (problem) {
      return (problem.tags || []).map(tag => typeof tag === 'string' ? tag : tag.name).filter(Boolean).slice(0, 2)
    },
    loadRanking (rule, fallback) {
      api.getUserRank(0, 5, rule).then(res => {
        const results = (res.data.data && res.data.data.results) || []
        this.rankings[rule] = results.length ? results : cloneFixtures(fallback).slice(0, 5)
      }).catch(() => { this.rankings[rule] = cloneFixtures(fallback).slice(0, 5) })
    },
    rankingUsername (row) {
      return (row.user && row.user.username) || row.username || ''
    },
    withContestProblems (contests) {
      return contests.map(contest => {
        const fixture = MOCK_CONTESTS.find(item => String(item.id) === String(contest.id))
        return fixture ? { ...contest, problem_ids: fixture.problem_ids } : contest
      })
    },
    go (path) { this.$router.push(path) },
    goContest (contest) { this.$router.push({ name: 'contest-problem-list', params: { contestID: contest.id } }) },
    goProblem (problem) { this.$router.push({ name: 'problem-details', params: { problemID: problem._id } }) },
    goUser (username) {
      if (username) this.$router.push({ name: 'user-home', query: { username } })
    }
  },
  computed: {
    rankingRows () {
      return this.rankings[this.rankingMode] || []
    }
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
.contest-card { appearance: none; display: flex; align-items: center; width: 100%; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); color: var(--color-text); text-align: left; cursor: pointer; transition: background-color var(--transition), border-color var(--transition), box-shadow var(--transition), transform 180ms ease; }
.contest-card:hover { background: var(--color-bg-subtle); border-color: var(--line-strong); box-shadow: var(--shadow-card); }
.contest-card:active { transform: scale(.99); }
.contest-main { display: flex; min-width: 0; flex: 1; flex-direction: column; gap: 3px; }.contest-main strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }.contest-main small { overflow: hidden; color: var(--color-text-muted); text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }.contest-arrow { flex: none; color: var(--color-text-faint); transform: rotate(-90deg); }
.home-columns { display: grid; grid-template-columns: minmax(0, 1fr) minmax(250px, .62fr); gap: 24px; padding-top: 30px; align-items: start; }
.home-left-column { display: grid; gap: 24px; min-width: 0; }
.home-right-column { display: grid; gap: 24px; min-width: 0; }
.home-columns > .home-section, .home-left-column > .home-section, .home-right-column > .home-section { padding-top: 0; }
.contest-list { display: grid; gap: 8px; }.contest-card { padding: 14px 16px; gap: 14px; }.contest-date { display: inline-flex; flex: 0 0 62px; width: 62px; align-items: center; white-space: nowrap; color: var(--cat-competition); font: 600 16px var(--font-serif); }.empty-card { padding: 26px; border: 1px dashed var(--color-border); border-radius: var(--radius-md); color: var(--color-text-faint); text-align: center; }
.problem-table-shell { overflow-x: auto; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); }
.home-problem-table { width: 100%; min-width: 610px; border-collapse: collapse; table-layout: fixed; }
.home-problem-table td { height: 46px; padding: 9px 13px; border-bottom: 1px solid var(--color-border); text-align: left; vertical-align: middle; }
.home-problem-table td:first-child { width: 104px; }
.home-problem-table td:nth-child(3) { width: 92px; }
.home-problem-table td:last-child { width: 178px; }
.home-problem-table tbody tr { transition: background-color var(--transition); }
.home-problem-table tbody tr:hover { background: rgba(55, 53, 47, .035); }
.home-problem-table tbody tr:last-child td { border-bottom: 0; }
.problem-title-cell { overflow: hidden; }
.problem-table-link { appearance: none; max-width: 100%; overflow: hidden; padding: 0; border: 0; background: transparent; color: var(--color-text); font: inherit; text-align: left; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }
.problem-table-link:hover, .problem-table-link:focus-visible { color: var(--color-link); }
.problem-display-id { color: var(--color-text-muted); font-family: var(--font-mono); font-size: 12px; font-weight: 650; }
.problem-table-title { display: block; width: 100%; font-size: 13px; font-weight: 600; }
.home-difficulty-badge { display: inline-flex; min-width: 54px; min-height: 23px; align-items: center; justify-content: center; padding: 0 8px; border: 1px solid transparent; border-radius: var(--radius-sm); font-size: 11px; font-weight: 650; line-height: 1; }
.home-difficulty-badge.difficulty-low { border-color: color-mix(in srgb, var(--cat-tools) 20%, transparent); background: var(--tag-tools-bg); color: var(--cat-tools); }
.home-difficulty-badge.difficulty-mid { border-color: color-mix(in srgb, var(--cat-kaggle) 20%, transparent); background: var(--tag-kaggle-bg); color: var(--cat-kaggle); }
.home-difficulty-badge.difficulty-high { border-color: color-mix(in srgb, var(--cat-research) 20%, transparent); background: var(--tag-research-bg); color: var(--cat-research); }
.home-problem-tags { display: flex; min-width: 0; align-items: center; gap: 5px; }
.home-problem-tags span { display: inline-flex; min-width: 0; max-width: 80px; min-height: 23px; align-items: center; overflow: hidden; padding: 0 7px; border-radius: var(--radius-sm); background: var(--color-bg-subtle); color: var(--color-text-muted); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.table-empty-value { color: var(--color-text-faint); font-size: 12px; }
.announcement-board { display: flex; min-height: 180px; overflow: hidden; flex-direction: column; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); }
.notice-board-header { display: flex; align-items: center; gap: 12px; padding: 14px 16px 9px; background: var(--color-bg); }
.notice-icon { display: grid; width: 32px; height: 32px; place-items: center; border-radius: var(--radius-sm); color: var(--cat-research); background: var(--tag-research-bg); }
.notice-board-header > span:last-child { display: flex; flex-direction: column; gap: 2px; }.notice-board-header strong { font-size: 14px; }.notice-board-header small { color: var(--color-text-muted); font-size: 12px; }
.ranking-board { overflow: hidden; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); }
.ranking-heading { align-items: center; }
.ranking-tabs { position: relative; display: grid; width: 170px; flex: none; grid-template-columns: repeat(2, minmax(0, 1fr)); padding: 2px; border: 1px solid var(--color-border); border-radius: 3px; background: var(--color-bg-subtle); }
.ranking-tabs::before { position: absolute; top: 2px; bottom: 2px; left: 2px; width: calc(50% - 2px); border: 1px solid var(--color-border); border-radius: 2px; background: var(--color-bg); box-shadow: 0 1px 3px rgba(55, 53, 47, .08); content: ''; transition: transform 180ms ease; }
.ranking-tabs.is-oi::before { transform: translateX(100%); }
.ranking-tabs button { position: relative; z-index: 1; min-width: 0; height: 28px; padding: 0 7px; border: 0; background: transparent; color: var(--color-text-faint); font: inherit; font-size: 11px; font-weight: 650; white-space: nowrap; cursor: pointer; transition: color var(--transition); }
.ranking-tabs button[aria-selected='true'] { color: var(--color-text); }
.home-ranking-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.home-ranking-table th, .home-ranking-table td { height: 42px; padding: 9px 14px; border-bottom: 1px solid var(--color-border); text-align: left; }
.home-ranking-table th { height: 40px; background: var(--color-bg); color: #1f1f1d; font-size: 14px; font-style: italic; font-weight: 750; }
.home-ranking-table th:first-child, .home-ranking-table td:first-child { width: 76px; text-align: center; }
.home-ranking-table tbody tr { transition: background-color var(--transition); }
.home-ranking-table tbody tr:hover { background: rgba(55, 53, 47, .035); }
.home-ranking-table tbody tr:last-child td { border-bottom: 0; }
.home-ranking-table td:first-child { color: var(--color-text-faint); font-family: var(--font-mono); font-size: 12px; font-weight: 650; }
.ranking-username { appearance: none; max-width: 100%; overflow: hidden; padding: 0; border: 0; background: transparent; color: var(--color-text); font: inherit; font-size: 13px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }
.ranking-username:hover, .ranking-username:focus-visible { color: var(--color-link); }
.announcement-section :deep(.el-card) { flex: 1; border: 0; border-radius: 0; box-shadow: none; }.announcement-section :deep(.panel-title) { font-size: inherit; }.announcement-section :deep(.el-card__header) { display: none; }.announcement-section :deep(.el-card__body) { padding: 0 16px; }.announcement-section :deep(.announcements-container) { margin: 0; padding: 0; }.announcement-section :deep(.announcements-container li) { margin: 0; padding: 13px 0; border-bottom: 1px solid var(--color-border); }.announcement-section :deep(.announcements-container li:last-child) { border-bottom: 0; }.announcement-section :deep(.flex-container) { align-items: center; }.announcement-section :deep(.creator) { display: none; }.announcement-section :deep(.date) { width: auto; color: var(--color-text-faint); font-size: 12px; }.announcement-section :deep(.title) { padding-left: 0; font-size: 14px; }.announcement-section :deep(.title a.entry) { color: var(--color-text); }.announcement-section :deep(.title a.entry:hover) { color: var(--color-link); }.announcement-section :deep(.no-announcement) { padding: 22px 0; color: var(--color-text-faint); font-size: 13px; }
@media (max-width: 900px) { .home-columns { grid-template-columns: 1fr; gap: 24px; padding-top: 0; } }
@media (max-width: 520px) { .home-page { padding-top: 4px; } .ranking-heading { gap: 10px; } .ranking-heading h2 { font-size: 21px; } .ranking-tabs { width: 154px; } }
</style>
