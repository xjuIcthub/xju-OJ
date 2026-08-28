<template>
  <section class="contest-problem-panel" aria-labelledby="contest-problem-title">
    <header class="problem-panel-header">
      <div>
        <p>{{$t('m.Problems')}}</p>
        <h2 id="contest-problem-title">{{$t('m.Problems_List')}}</h2>
      </div>
      <span class="problem-count">{{problems.length}}</span>
    </header>

    <div v-if="problems.length" class="problem-table-wrap">
      <table class="contest-problem-table">
        <thead>
          <tr>
            <th class="problem-id">#</th>
            <th>{{$t('m.Title')}}</th>
            <th v-if="showStatistics" class="numeric">{{$t('m.Total')}}</th>
            <th v-if="showStatistics" class="numeric">{{$t('m.AC_Rate')}}</th>
            <th v-if="showUserStatus" class="problem-status">{{$t('m.Status')}}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(problem, index) in problems"
              :key="problem._id"
              tabindex="0"
              @click="goContestProblem(problem)"
              @keydown.enter.prevent="goContestProblem(problem)">
            <td class="problem-id"><span>{{problemLabel(problem, index)}}</span></td>
            <td>
              <router-link class="problem-title-link" :to="problemRoute(problem)" @click.stop>
                <strong>{{problem.title}}</strong>
                <Icon type="arrow-down-b" />
              </router-link>
            </td>
            <td v-if="showStatistics" class="numeric">{{problem.submission_number || 0}}</td>
            <td v-if="showStatistics" class="numeric">{{getACRate(problem.accepted_number, problem.submission_number)}}</td>
            <td v-if="showUserStatus" class="problem-status">
              <span v-if="problem.my_status === 0" class="attempt-status is-accepted">
                <Icon type="check" />{{$t('m.Accepted')}}
              </span>
              <span v-else-if="problem.my_status !== null && problem.my_status !== undefined" class="attempt-status is-attempted">
                <Icon type="refresh" />{{$t('m.Submissions')}}
              </span>
              <span v-else class="attempt-status is-empty">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="problem-empty">
      <Icon type="ios-photos" />
      <p>{{$t('m.No_Problems')}}</p>
    </div>
  </section>
</template>

<script>
  import { mapState, mapGetters } from '@/store/compat'
  import utils from '@/utils/utils'

  export default {
    name: 'ContestProblemList',
    mounted () {
      this.$store.dispatch('getContestProblems')
    },
    methods: {
      getACRate (accepted, total) {
        return utils.getACRate(accepted, total)
      },
      problemLabel (problem, index) {
        return problem._id || String.fromCharCode(65 + index)
      },
      problemRoute (problem) {
        return {
          name: 'contest-problem-details',
          params: {
            contestID: this.$route.params.contestID,
            problemID: problem._id
          }
        }
      },
      goContestProblem (problem) {
        this.$router.push(this.problemRoute(problem))
      }
    },
    computed: {
      ...mapState({
        problems: state => state.contest.contestProblems
      }),
      ...mapGetters(['isAuthenticated', 'contestRuleType', 'OIContestRealTimePermission']),
      showStatistics () {
        return this.contestRuleType === 'ACM' || this.OIContestRealTimePermission
      },
      showUserStatus () {
        return this.isAuthenticated && this.problems.some(problem => problem.my_status !== null && problem.my_status !== undefined)
      }
    }
  }
</script>

<style scoped lang="less">
  .contest-problem-panel {
    overflow: hidden;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    box-shadow: var(--shadow-card);
  }

  .problem-panel-header {
    display: flex;
    min-height: 76px;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 16px 20px;
    border-bottom: 1px solid var(--color-border);
  }
  .problem-panel-header p { margin: 0 0 2px; color: var(--color-text-faint); font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
  .problem-panel-header h2 { margin: 0; font-family: var(--font-serif); font-size: 21px; font-weight: 650; }
  .problem-count { display: inline-flex; min-width: 28px; height: 24px; align-items: center; justify-content: center; padding: 0 8px; border-radius: var(--radius-sm); background: var(--color-bg-subtle); color: var(--color-text-muted); font-size: 12px; font-weight: 650; }

  .problem-table-wrap { overflow-x: auto; }
  .contest-problem-table { width: 100%; min-width: 620px; border-collapse: collapse; table-layout: auto; }
  .contest-problem-table th, .contest-problem-table td { padding: 13px 18px; border-bottom: 1px solid var(--color-border); text-align: left; }
  .contest-problem-table th { background: #fcfbf9; color: var(--color-text-muted); font-size: 11px; font-weight: 700; letter-spacing: .035em; text-transform: uppercase; }
  .contest-problem-table tbody tr { cursor: pointer; transition: background-color var(--transition); }
  .contest-problem-table tbody tr:last-child td { border-bottom: 0; }
  .contest-problem-table tbody tr:hover, .contest-problem-table tbody tr:focus { background: var(--color-bg-subtle); outline: 0; }
  .contest-problem-table tbody tr:focus-visible { box-shadow: inset 3px 0 var(--color-text); }
  .contest-problem-table .problem-id { width: 92px; }
  .contest-problem-table td.problem-id span { display: inline-flex; min-width: 40px; height: 25px; align-items: center; justify-content: center; padding: 0 8px; border-radius: var(--radius-sm); background: var(--color-bg-subtle); color: var(--color-text); font-family: var(--font-mono); font-size: 12px; font-weight: 700; }
  .contest-problem-table .numeric { width: 120px; text-align: right; font-variant-numeric: tabular-nums; }
  .contest-problem-table .problem-status { width: 138px; text-align: right; }

  .problem-title-link { display: inline-flex; max-width: 100%; align-items: center; gap: 8px; color: var(--color-text); }
  .problem-title-link strong { overflow: hidden; font-size: 14px; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }
  .problem-title-link :deep(svg) { flex: none; width: 14px; height: 14px; color: var(--color-text-faint); transform: rotate(-90deg); transition: color var(--transition), transform var(--transition); }
  .problem-title-link:hover { color: var(--color-link); }
  .problem-title-link:hover :deep(svg) { color: var(--color-link); transform: rotate(-90deg) translateY(2px); }

  .attempt-status { display: inline-flex; min-height: 24px; align-items: center; justify-content: center; gap: 5px; padding: 3px 8px; border-radius: var(--radius-sm); font-size: 11px; font-weight: 650; white-space: nowrap; }
  .attempt-status :deep(svg) { width: 13px; height: 13px; }
  .attempt-status.is-accepted { background: var(--tag-tools-bg); color: var(--cat-tools); }
  .attempt-status.is-attempted { background: var(--tag-course-bg); color: var(--cat-course); }
  .attempt-status.is-empty { background: transparent; color: var(--color-text-faint); }

  .problem-empty { display: flex; min-height: 220px; align-items: center; justify-content: center; flex-direction: column; gap: 10px; color: var(--color-text-faint); }
  .problem-empty :deep(svg) { width: 28px; height: 28px; }
  .problem-empty p { margin: 0; }

  @media (max-width: 620px) {
    .problem-panel-header { min-height: 68px; padding: 14px 16px; }
    .contest-problem-table th, .contest-problem-table td { padding: 12px 14px; }
  }

  @media (prefers-reduced-motion: reduce) {
    .contest-problem-table tbody tr, .problem-title-link :deep(svg) { transition: none; }
  }
</style>
