<template>
  <div class="view">
    <Panel :title="contestId ? this.$t('m.Contest_Problem_List') : this.$t('m.Problem_List')">
      <template #header><div >
        <el-input
          v-model="keyword"
          placeholder="Keywords">
          <template #prefix><Icon type="search" /></template>
        </el-input>
      </div></template>
      <el-table
        v-loading="loading"
        element-loading-text="loading"
        ref="table"
        :data="problemList"
        @row-dblclick="handleDblclick"
        style="width: 100%">
        <el-table-column
          width="100"
          prop="id"
          label="ID">
        </el-table-column>
        <el-table-column
          width="150"
          label="Display ID">
          <template #default="{row}">
            <span v-show="!row.isEditing">{{row._id}}</span>
            <el-input v-show="row.isEditing" v-model="row._id"
                      @keyup.enter="handleInlineEdit(row)">

            </el-input>
          </template>
        </el-table-column>
        <el-table-column
          prop="title"
          label="Title">
          <template #default="{row}">
            <span v-show="!row.isEditing">{{row.title}}</span>
            <el-input v-show="row.isEditing" v-model="row.title"
                      @keyup.enter="handleInlineEdit(row)">
            </el-input>
          </template>
        </el-table-column>
        <el-table-column
          prop="created_by.username"
          label="Author">
        </el-table-column>
        <el-table-column
          width="200"
          prop="create_time"
          label="Create Time">
          <template #default="scope">
            {{ $filters.localtime(scope.row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column
          width="100"
          prop="visible"
          label="Visible">
          <template #default="scope">
            <el-switch v-model="scope.row.visible"
                       active-text=""
                       inactive-text=""
                       @change="updateProblem(scope.row)">
            </el-switch>
          </template>
        </el-table-column>
        <el-table-column
          width="120"
          label="Judge">
          <template #default="scope">
            {{ scope.row.judge_mode === 'REMOTE' ? scope.row.remote_oj : 'LOCAL' }}
          </template>
        </el-table-column>
        <el-table-column
          fixed="right"
          label="Operation"
          width="168">
          <template #default="scope"><div >
            <icon-btn name="Edit" icon="edit" @click="goEdit(scope.row.id)"></icon-btn>
            <icon-btn v-if="contestId" name="Make Public" icon="clone"
                      @click="makeContestProblemPublic(scope.row.id)"></icon-btn>
            <icon-btn v-if="scope.row.judge_mode !== 'REMOTE'"
                      icon="download" name="Download TestCase"
                      @click="downloadTestCase(scope.row.id)"></icon-btn>
            <icon-btn icon="trash" name="Delete Problem"
                      @click="deleteProblem(scope.row.id)"></icon-btn>
          </div></template>
        </el-table-column>
      </el-table>
      <div class="panel-options">
        <el-button type="primary" size="small"
                   @click="goCreateProblem"><Icon type="plus" />Create
        </el-button>
        <el-button v-if="!contestId" type="success" size="small"
                   @click="remoteImportDialogVisible = true"><Icon type="download" />Import Remote
        </el-button>
        <el-button v-if="contestId" type="success" size="small"
                   @click="remoteImportDialogVisible = true"><Icon type="download" />Import Remote
        </el-button>
        <el-button v-if="contestId" type="primary"
                   size="small"
                   @click="addProblemDialogVisible = true"><Icon type="plus" />Add From Public Problem
        </el-button>
        <el-pagination
          class="page"
          layout="prev, pager, next"
          @current-change="currentChange"
          :page-size="pageSize"
          :total="total">
        </el-pagination>
      </div>
    </Panel>
    <LegacyDialog title="Sure to update the problem? "
               width="20%"
               :visible="InlineEditDialogVisible" @update:visible="InlineEditDialogVisible = $event"
               @close-on-click-modal="false">
      <div>
        <p>DisplayID: {{currentRow._id}}</p>
        <p>Title: {{currentRow.title}}</p>
      </div>
      <template #footer><span >
        <cancel @click="InlineEditDialogVisible = false; getProblemList(currentPage)"></cancel>
        <save @click="updateProblem(currentRow)"></save>
      </span></template>
    </LegacyDialog>
    <LegacyDialog title="Add Contest Problem"
               v-if="contestId"
               width="80%"
               :visible="addProblemDialogVisible" @update:visible="addProblemDialogVisible = $event"
               @close-on-click-modal="false">
      <add-problem-component :contestID="contestId" @on-change="getProblemList"></add-problem-component>
    </LegacyDialog>
    <LegacyDialog :title="contestId ? 'Import Remote Problem Into Contest' : 'Import Remote Problem'"
               width="520px"
               :visible="remoteImportDialogVisible" @update:visible="remoteImportDialogVisible = $event"
               @close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="Remote OJ" required>
          <el-select v-model="remoteImportForm.provider" style="width: 100%">
            <el-option label="Nowcoder / 牛客" value="NOWCODER"></el-option>
            <el-option label="Luogu / 洛谷" value="LUOGU"></el-option>
            <el-option label="Codeforces" value="CODEFORCES"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="remoteImportIdLabel" required>
          <el-input v-model="remoteImportForm.remote_id"
                    :placeholder="remoteImportPlaceholder"></el-input>
        </el-form-item>
        <el-form-item :label="contestId ? 'Contest Display ID' : 'Display ID'"
                      :required="Boolean(contestId)">
          <el-input v-model="remoteImportForm.display_id"
                    :placeholder="remoteImportDisplayIdPlaceholder"></el-input>
        </el-form-item>
        <el-form-item v-if="contestId" label="Public Library Display ID">
          <el-input v-model="remoteImportForm.public_display_id"
                    :placeholder="remoteImportPublicDisplayIdPlaceholder"></el-input>
        </el-form-item>
        <el-alert type="info" :closable="false"
                  :title="contestId
                    ? 'If this is a new remote problem, it will automatically enter the public library after the contest ends.'
                    : 'The imported problem is immediately available for remote practice submissions.'"></el-alert>
      </el-form>
      <template #footer><span>
        <cancel @click="remoteImportDialogVisible = false"></cancel>
        <el-button type="primary" :loading="remoteImportLoading"
                   @click="importRemoteProblem">Import</el-button>
      </span></template>
    </LegacyDialog>
  </div>
</template>
<script>
  import api from '../../api.js'
  import utils from '@/utils/utils'
  import AddProblemComponent from './AddPublicProblem.vue'
  import { collectCodeforcesProblemPage, supportsRemoteProblemImport } from '../../remoteBridge'

  export default {
    name: 'ProblemList',
    components: {
      AddProblemComponent
    },
    data () {
      return {
        pageSize: 10,
        total: 0,
        problemList: [],
        keyword: '',
        loading: false,
        currentPage: 1,
        routeName: '',
        contestId: '',
        // for make public use
        currentProblemID: '',
        currentRow: {},
        InlineEditDialogVisible: false,
        makePublicDialogVisible: false,
        addProblemDialogVisible: false,
        remoteImportDialogVisible: false,
        remoteImportLoading: false,
        remoteImportForm: {
          provider: 'NOWCODER',
          remote_id: '',
          display_id: '',
          public_display_id: ''
        }
      }
    },
    mounted () {
      this.routeName = this.$route.name
      this.contestId = this.$route.params.contestId
      this.getProblemList(this.currentPage)
    },
    computed: {
      remoteImportIdLabel () {
        return {
          NOWCODER: 'Nowcoder NC problem ID or ACM problem URL',
          LUOGU: 'Luogu problem ID or URL',
          CODEFORCES: 'Codeforces problem ID or URL'
        }[this.remoteImportForm.provider]
      },
      remoteImportPlaceholder () {
        return {
          NOWCODER: 'NC322024 or https://ac.nowcoder.com/acm/problem/322024',
          LUOGU: 'P1001',
          CODEFORCES: '4A'
        }[this.remoteImportForm.provider]
      },
      remoteImportDisplayIdPlaceholder () {
        if (this.contestId) return 'A, B, C...'
        return {
          NOWCODER: 'Leave blank to use NC322024',
          LUOGU: 'Leave blank to use LG-P1001',
          CODEFORCES: 'Leave blank to use CF-4A'
        }[this.remoteImportForm.provider]
      },
      remoteImportPublicDisplayIdPlaceholder () {
        return {
          NOWCODER: 'Leave blank to use NC322024',
          LUOGU: 'Leave blank to use LG-P1001',
          CODEFORCES: 'Leave blank to use CF-4A'
        }[this.remoteImportForm.provider]
      }
    },
    methods: {
      handleDblclick (row) {
        row.isEditing = true
      },
      goEdit (problemId) {
        if (this.routeName === 'problem-list') {
          this.$router.push({name: 'edit-problem', params: {problemId}})
        } else if (this.routeName === 'contest-problem-list') {
          this.$router.push({name: 'edit-contest-problem', params: {problemId: problemId, contestId: this.contestId}})
        }
      },
      goCreateProblem () {
        if (this.routeName === 'problem-list') {
          this.$router.push({name: 'create-problem'})
        } else if (this.routeName === 'contest-problem-list') {
          this.$router.push({name: 'create-contest-problem', params: {contestId: this.contestId}})
        }
      },
      async importRemoteProblem () {
        if (!this.remoteImportForm.remote_id.trim()) {
          this.$error('Remote problem ID or URL is required')
          return
        }
        if (this.contestId && !this.remoteImportForm.display_id.trim()) {
          this.$error('Contest display ID is required')
          return
        }
        this.remoteImportLoading = true
        let pageHtml = ''
        if (this.remoteImportForm.provider === 'CODEFORCES') {
          if (!supportsRemoteProblemImport()) {
            this.remoteImportLoading = false
            this.$error('Codeforces 导题需要最新版远程提交助手，已为你打开安装页')
            window.open('/remote-bridge', '_blank', 'noopener')
            return
          }
          try {
            pageHtml = await collectCodeforcesProblemPage(this.remoteImportForm.remote_id.trim())
          } catch (error) {
            this.remoteImportLoading = false
            this.$error(error.message || 'Codeforces 题面读取失败')
            return
          }
        }
        api.importRemoteProblem({
          provider: this.remoteImportForm.provider,
          remote_id: this.remoteImportForm.remote_id.trim(),
          display_id: this.remoteImportForm.display_id.trim(),
          contest_id: this.contestId || null,
          public_display_id: this.remoteImportForm.public_display_id.trim(),
          page_html: pageHtml
        }).then(() => {
          this.remoteImportLoading = false
          this.remoteImportDialogVisible = false
          this.remoteImportForm = {
            provider: 'NOWCODER',
            remote_id: '',
            display_id: '',
            public_display_id: ''
          }
          this.$success('Remote problem imported')
          this.getProblemList(1)
        }).catch(() => {
          this.remoteImportLoading = false
        })
      },
      // 切换页码回调
      currentChange (page) {
        this.currentPage = page
        this.getProblemList(page)
      },
      getProblemList (page = 1) {
        this.loading = true
        let funcName = this.routeName === 'problem-list' ? 'getProblemList' : 'getContestProblemList'
        let params = {
          limit: this.pageSize,
          offset: (page - 1) * this.pageSize,
          keyword: this.keyword,
          contest_id: this.contestId
        }
        api[funcName](params).then(res => {
          this.loading = false
          this.total = res.data.data.total
          for (let problem of res.data.data.results) {
            problem.isEditing = false
          }
          this.problemList = res.data.data.results
        }, res => {
          this.loading = false
        })
      },
      deleteProblem (id) {
        this.$confirm('Sure to delete this problem? The associated submissions will be deleted as well.', 'Delete Problem', {
          type: 'warning'
        }).then(() => {
          let funcName = this.routeName === 'problem-list' ? 'deleteProblem' : 'deleteContestProblem'
          api[funcName](id).then(() => [
            this.getProblemList(this.currentPage - 1)
          ]).catch(() => {
          })
        }, () => {
        })
      },
      makeContestProblemPublic (problemID) {
        this.$prompt('Please input display id for the public problem', 'confirm').then(({value}) => {
          api.makeContestProblemPublic({id: problemID, display_id: value}).catch()
        }, () => {
        })
      },
      updateProblem (row) {
        let data = Object.assign({}, row)
        let funcName = ''
        if (this.contestId) {
          data.contest_id = this.contestId
          funcName = 'editContestProblem'
        } else {
          funcName = 'editProblem'
        }
        api[funcName](data).then(res => {
          this.InlineEditDialogVisible = false
          this.getProblemList(this.currentPage)
        }).catch(() => {
          this.InlineEditDialogVisible = false
        })
      },
      handleInlineEdit (row) {
        this.currentRow = row
        this.InlineEditDialogVisible = true
      },
      downloadTestCase (problemID) {
        let url = '/admin/test_case?problem_id=' + problemID
        utils.downloadFile(url)
      },
      getPublicProblem () {
        api.getProblemList()
      }
    },
    watch: {
      '$route' (newVal, oldVal) {
        this.contestId = newVal.params.contestId
        this.routeName = newVal.name
        this.getProblemList(this.currentPage)
      },
      'keyword' () {
        this.currentChange()
      }
    }
  }
</script>

<style scoped lang="less">
</style>
