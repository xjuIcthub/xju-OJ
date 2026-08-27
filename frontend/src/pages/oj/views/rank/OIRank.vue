<template>
  <section class="rank-page">
    <div class="rank-heading">
      <h1>{{$t('m.OI_Ranklist')}}</h1>
      <span>{{$t('m.OI_Standings')}}</span>
    </div>
    <Table class="rank-table" :data="dataRank" :columns="columns" :loading="loadingTable" size="large"></Table>
    <Pagination :total="total" :page-size="limit" @update:page-size="limit = $event" :current="page" @update:current="page = $event"
                @on-change="getRankData" show-sizer @on-page-size-change="getRankData(1)"></Pagination>
  </section>
</template>
<script>
  import api from '@oj/api'
  import Pagination from '@oj/components/Pagination'
  import utils from '@/utils/utils'
  import { RULE_TYPE } from '@/utils/constants'
  import { cloneFixtures, MOCK_OI_RANK } from '@oj/mocks/fixtures'

  export default {
    name: 'oi-rank',
    components: {
      Pagination
    },
    data () {
      return {
        page: 1,
        limit: 30,
        total: 0,
        loadingTable: false,
        dataRank: [],
        columns: [
          {
            title: '#',
            align: 'center',
            width: 60,
            render: (h, params) => {
              return h('span', {}, params.index + (this.page - 1) * this.limit + 1)
            }
          },
          {
            title: this.$t('m.User_User'),
            align: 'center',
            render: (h, params) => {
              return h('a', {
                style: {
                  'display': 'inline-block',
                  'max-width': '200px'
                },
                on: {
                  click: () => {
                    this.$router.push({
                      name: 'user-home',
                      query: {username: params.row.user.username}
                    })
                  }
                }
              }, params.row.user.username)
            }
          },
          {
            title: this.$t('m.mood'),
            align: 'center',
            key: 'mood'
          },
          {
            title: this.$t('m.Score'),
            align: 'center',
            key: 'total_score'
          },
          {
            title: this.$t('m.AC'),
            align: 'center',
            key: 'accepted_number'
          },
          {
            title: this.$t('m.Total'),
            align: 'center',
            key: 'submission_number'
          },
          {
            title: this.$t('m.Rating'),
            align: 'center',
            render: (h, params) => {
              return h('span', utils.getACRate(params.row.accepted_number, params.row.submission_number))
            }
          }
        ]
      }
    },
    mounted () {
      this.getRankData(1)
    },
    methods: {
      getRankData (page = 1) {
        this.page = page
        const offset = (page - 1) * this.limit
        this.loadingTable = true
        api.getUserRank(offset, this.limit, RULE_TYPE.OI).then(res => {
          const payload = res.data.data || {}
          const results = payload.results || []
          this.dataRank = results.length ? results : cloneFixtures(MOCK_OI_RANK)
          this.total = payload.total || this.dataRank.length
          this.loadingTable = false
        }).catch(() => {
          this.dataRank = cloneFixtures(MOCK_OI_RANK)
          this.total = this.dataRank.length
          this.loadingTable = false
        })
      }
    }
  }
</script>

<style scoped lang="less">
  /* Direct table layout: keep rankings free of the legacy chart card. */
  .rank-page {
    width: 100%;
    padding-top: 22px;
  }

  .rank-heading {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 14px;
  }

  .rank-heading h1 {
    margin: 0;
    color: var(--color-text);
    font: 600 26px/1.2 var(--font-serif);
  }

  .rank-heading span {
    color: var(--color-text-faint);
    font-size: 12px;
  }

  .rank-table :deep(.el-table),
  .rank-table :deep(.el-table__inner-wrapper),
  .rank-table :deep(.ivu-table-wrapper) {
    border: 0;
    border-radius: 0;
    box-shadow: none;
  }

  .rank-table :deep(.el-table__header-wrapper th.el-table__cell) {
    height: 44px;
  }

  .rank-table :deep(.el-table__body-wrapper td.el-table__cell) {
    height: 48px;
  }
</style>
