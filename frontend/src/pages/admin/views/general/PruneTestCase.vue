<template>
  <div>
    <panel>
      <template #title><span >{{$t('m.Test_Case_Prune_Test_Case')}}
        <el-popover placement="right" trigger="hover">
          这些测试数据未被任何题目使用，可以安全清理。
          <template #reference><Icon type="question-circle" class="import-user-icon" /></template>
        </el-popover>
      </span></template>
      <el-table :data="data">
        <el-table-column
          label="最后修改时间">
          <template #default="{row}">
            {{ $filters.timestampFormat(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="id"
          label="测试数据 ID">
        </el-table-column>
        <el-table-column
          label="操作"
          fixed="right"
          width="72">
          <template #default="{row}">
            <icon-btn danger name="删除" icon="trash" @click="deleteTestCase(row.id)"></icon-btn>
          </template>
        </el-table-column>
      </el-table>
      <div class="panel-options" v-show="data.length > 0">
        <el-button type="warning" size="small"
                   :loading="loading"
                   @click="deleteTestCase()"><Icon type="trash" />全部删除
        </el-button>
      </div>
    </panel>
  </div>
</template>
<script>
  import api from '@admin/api'
  import moment from 'moment'

  export default {
    name: 'prune-test-case',
    data () {
      return {
        data: [],
        loading: false
      }
    },
    mounted () {
      this.init()
    },
    methods: {
      init () {
        api.getInvalidTestCaseList().then(resp => {
          this.data = resp.data.data
        }, () => {
        })
      },
      deleteTestCase (id) {
        if (!id) {
          this.loading = true
        }
        api.pruneTestCase(id).then(resp => {
          this.loading = false
          this.init()
        })
      }
    },
    filters: {
      timestampFormat (value) {
        return moment.unix(value).format('YYYY-M-D  HH:mm:ss')
      }
    }
  }
</script>

<style>

</style>
