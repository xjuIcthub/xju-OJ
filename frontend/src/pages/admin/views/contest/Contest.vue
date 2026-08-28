<template>
  <div class="view">
    <Panel :title="title">
      <el-form label-position="top">
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item :label="$t('m.ContestTitle')" required>
              <el-input v-model="contest.title" :placeholder="$t('m.ContestTitle')"></el-input>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item :label="$t('m.ContestDescription')" required>
              <Simditor v-model="contest.description"></Simditor>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="$t('m.Contest_Start_Time')" required>
              <el-date-picker
                v-model="contest.start_time"
                type="datetime"
                :placeholder="$t('m.Contest_Start_Time')">
              </el-date-picker>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="$t('m.Contest_End_Time')" required>
              <el-date-picker
                v-model="contest.end_time"
                type="datetime"
                :placeholder="$t('m.Contest_End_Time')">
              </el-date-picker>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="$t('m.Contest_Password')">
              <el-input v-model="contest.password" :placeholder="$t('m.Contest_Password')"></el-input>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <div class="inline-setting">
              <span>{{ $t('m.Contest_Rule_Type') }}</span>
              <el-radio-group v-model="contest.rule_type" :disabled="disableRuleType">
                <el-radio class="radio rule-type-acm" label="ACM">ACM</el-radio>
                <el-radio class="radio rule-type-oi" label="OI">OI</el-radio>
              </el-radio-group>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="inline-setting">
              <span>{{ $t('m.Real_Time_Rank') }}</span>
              <el-switch
                v-model="contest.real_time_rank"
                active-color="#13ce66"
                inactive-color="#ff4949">
              </el-switch>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="inline-setting">
              <span>{{ $t('m.Contest_Status') }}</span>
              <el-switch
                v-model="contest.visible"
                active-text=""
                inactive-text="">
              </el-switch>
            </div>
          </el-col>
        </el-row>
      </el-form>
      <ContestProblemComposer v-if="isCreate"
                              ref="problemComposer"
                              v-model="problemPlan"
                              :rule-type="contest.rule_type" />
      <save @click="saveContest"></save>
    </Panel>
  </div>
</template>

<script>
  import api from '../../api.js'
  import Simditor from '../../components/Simditor.vue'
  import ContestProblemComposer from './ContestProblemComposer.vue'

  export default {
    name: 'CreateContest',
    components: {
      Simditor,
      ContestProblemComposer
    },
    data () {
      return {
        title: 'Create Contest',
        disableRuleType: false,
        problemPlan: [],
        saving: false,
        contest: {
          title: '',
          description: '',
          start_time: '',
          end_time: '',
          rule_type: 'ACM',
          password: '',
          real_time_rank: true,
          visible: true,
          allowed_ip_ranges: []
        }
      }
    },
    computed: {
      isCreate () {
        return this.$route.name !== 'edit-contest'
      }
    },
    methods: {
      async saveContest () {
        if (this.saving) return
        const incompatibleProblem = this.problemPlan.find(item => (
          (item.kind === 'REMOTE' && this.contest.rule_type !== 'ACM') ||
          (item.kind === 'PUBLIC' && item.ruleType && item.ruleType !== this.contest.rule_type)
        ))
        if (incompatibleProblem) {
          this.$error('题目编排中存在与当前比赛规则不兼容的题目，请先删除或切回对应规则')
          return
        }
        this.saving = true
        let funcName = this.$route.name === 'edit-contest' ? 'editContest' : 'createContest'
        let data = Object.assign({}, this.contest)
        data.allowed_ip_ranges = Array.isArray(data.allowed_ip_ranges) ? data.allowed_ip_ranges : []
        try {
          const res = await api[funcName](data)
          const contestId = (res.data.data || {}).id
          if (this.isCreate && this.problemPlan.length) {
            try {
              await this.$refs.problemComposer.materialize(contestId)
            } catch (error) {
              this.$error(`比赛已创建，但题目编排未全部完成：${error.message || '导入失败'}`)
              this.$router.push({name: 'contest-problem-list', params: {contestId}})
              return
            }
          }
          this.$router.push({name: 'contest-list', query: {refresh: 'true'}})
        } catch (error) {
          this.$error(error.message || '比赛保存失败')
        } finally {
          this.saving = false
        }
      }
    },
    mounted () {
      if (this.$route.name === 'edit-contest') {
        this.title = 'Edit Contest'
        this.disableRuleType = true
        api.getContest(this.$route.params.contestId).then(res => {
          this.contest = res.data.data
        }).catch(() => {
        })
      }
    }
  }
</script>

<style scoped lang="less">
:deep(.rule-type-acm .el-radio__label) { color: #b7791f; font-weight: 700; }
:deep(.rule-type-oi .el-radio__label) { color: #7656c9; font-weight: 700; }
.inline-setting { display: flex; min-height: 42px; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 18px; padding: 0 13px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: var(--color-bg); }
.inline-setting > span { color: var(--color-text-muted); font-size: 13px; font-weight: 600; }
:deep(.inline-setting .el-radio) { margin-right: 12px; }
</style>
