<template>
  <div class="view">
    <Panel :title="$t('m.Judge_Server_Token')">
      <code>{{ token }}</code>
    </Panel>
    <Panel :title="$t('m.Judge_Server_Info')">
      <el-table
        :data="servers"
        :default-expand-all="true"
        border>
        <el-table-column
          type="expand">
          <template #default="props">
            <div class="server-details">
              <div class="server-detail"><span>{{$t('m.IP')}}</span><el-tag type="success">{{ props.row.ip }}</el-tag></div>
              <div class="server-detail"><span>{{$t('m.Judger_Version')}}</span><el-tag type="success">{{ props.row.judger_version }}</el-tag></div>
              <div class="server-detail is-wide"><span>{{$t('m.Service_URL')}}</span><code>{{ props.row.service_url }}</code></div>
              <div class="server-detail"><span>{{$t('m.Last_Heartbeat')}}</span><strong>{{ $filters.localtime(props.row.last_heartbeat) }}</strong></div>
              <div class="server-detail"><span>{{$t('m.Create_Time')}}</span><strong>{{ $filters.localtime(props.row.create_time) }}</strong></div>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          prop="status"
          label="状态">
          <template #default="scope">
            <el-tag
              :type="scope.row.status === 'normal' ? 'success' : 'danger'">
              {{ scope.row.status === 'normal' ? '正常' : '异常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="hostname"
          label="主机名">
        </el-table-column>
        <el-table-column
          prop="task_number"
          label="任务数">
        </el-table-column>
        <el-table-column
          prop="cpu_core"
          label="CPU 核心">
        </el-table-column>
        <el-table-column
          prop="cpu_usage"
          label="CPU 使用率">
          <template #default="scope">{{ scope.row.cpu_usage }}%</template>
        </el-table-column>
        <el-table-column
          prop="memory_usage"
          label="内存使用率">
          <template #default="scope">{{ scope.row.memory_usage }}%</template>
        </el-table-column>
        <el-table-column label="已禁用">
          <template #default="{row}">
            <el-switch v-model="row.is_disabled" @change="handleDisabledSwitch(row.id, row.is_disabled)"></el-switch>
          </template>
        </el-table-column>
        <el-table-column
          fixed="right"
          label="操作"
          width="96">
          <template #default="scope">
            <icon-btn danger name="删除" icon="trash" @click="deleteJudgeServer(scope.row.hostname)"></icon-btn>
          </template>
        </el-table-column>
      </el-table>
    </Panel>
  </div>
</template>
<script>
  import api from '../../api.js'

  export default {
    name: 'JudgeServer',
    data () {
      return {
        servers: [],
        token: '',
        intervalId: -1
      }
    },
    mounted () {
      this.refreshJudgeServerList()
      this.intervalId = setInterval(() => {
        this.refreshJudgeServerList()
      }, 5000)
    },
    methods: {
      refreshJudgeServerList () {
        api.getJudgeServer().then(res => {
          this.servers = res.data.data.servers
          this.token = res.data.data.token
        })
      },
      deleteJudgeServer (hostname) {
        this.$confirm('删除后，该判题服务器需等待下一次心跳才能重新使用。', '删除判题服务器', {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning'
        }).then(() => {
          api.deleteJudgeServer(hostname).then(res =>
            this.refreshJudgeServerList()
          )
        }).catch(() => {
        })
      },
      handleDisabledSwitch (id, value) {
        let data = {
          id,
          is_disabled: value
        }
        api.updateJudgeServer(data).catch(() => {})
      }
    },
    beforeRouteLeave () {
      clearInterval(this.intervalId)
    }
  }
</script>
<style scoped lang="less">
.server-details { display: grid; grid-template-columns: repeat(2, minmax(220px, 1fr)); gap: 10px 24px; padding: 4px 0; }
.server-detail { display: flex; align-items: center; gap: 10px; min-width: 0; }
.server-detail > span { flex: 0 0 112px; color: var(--color-text-faint); font-size: 12px; }
.server-detail strong, .server-detail code { color: var(--color-text); font-weight: 600; }
.server-detail.is-wide { grid-column: 1 / -1; }
:deep(.el-table__expanded-cell) { padding: 14px 18px !important; background: var(--color-bg-subtle); }
@media (max-width: 1080px) { .server-details { grid-template-columns: 1fr; } .server-detail.is-wide { grid-column: auto; } }
</style>
