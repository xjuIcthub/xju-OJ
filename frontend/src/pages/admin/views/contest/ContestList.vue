<template>
  <div class="view">
    <Panel title="Contest List">
      <template #header><div >
        <el-input
          v-model="keyword"
          prefix-icon="el-icon-search"
          placeholder="Keywords">
        </el-input>
      </div></template>
      <el-table
        v-loading="loading"
        element-loading-text="loading"
        ref="table"
        :data="contestList"
        style="width: 100%">
        <el-table-column type="expand">
          <template #default="props">
            <p>Start Time: {{ $filters.localtime(props.row.start_time) }}</p>
            <p>End Time: {{ $filters.localtime(props.row.end_time) }}</p>
            <p>Create Time: {{ $filters.localtime(props.row.create_time) }}</p>
            <p>Creator: {{props.row.created_by.username}}</p>
          </template>
        </el-table-column>
        <el-table-column
          prop="id"
          width="80"
          label="ID">
        </el-table-column>
        <el-table-column
          prop="title"
          label="Title">
        </el-table-column>
        <el-table-column
          label="Rule Type"
          width="130">
          <template #default="scope">
            <el-tag type="gray">{{scope.row.rule_type}}</el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="Contest Type"
          width="180">
          <template #default="scope">
            <el-tag :type="scope.row.contest_type === 'Public' ? 'success' : 'primary'">
              {{ scope.row.contest_type}}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="Status"
          width="130">
          <template #default="scope">
            <el-tag
              :type="scope.row.status === '-1' ? 'danger' : scope.row.status === '0' ? 'success' : 'primary'">
              {{ $filters.contestStatus(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          width="100"
          label="Visible">
          <template #default="scope">
            <el-switch v-model="scope.row.visible"
                       active-text=""
                       inactive-text=""
                       @change="handleVisibleSwitch(scope.row)">
            </el-switch>
          </template>
        </el-table-column>
        <el-table-column
          fixed="right"
          width="250"
          label="Operation">
          <template #default="scope"><div >
            <icon-btn name="Edit" icon="edit" @click="goEdit(scope.row.id)"></icon-btn>
            <icon-btn name="Problem" icon="list-ol" @click="goContestProblemList(scope.row.id)"></icon-btn>
            <icon-btn name="Announcement" icon="info-circle"
                      @click="goContestAnnouncement(scope.row.id)"></icon-btn>
            <icon-btn icon="download" name="Download Accepted Submissions"
                      @click="openDownloadOptions(scope.row.id)"></icon-btn>
          </div></template>
        </el-table-column>
      </el-table>
      <div class="panel-options">
        <el-pagination
          class="page"
          layout="prev, pager, next"
          @current-change="currentChange"
          :page-size="pageSize"
          :total="total">
        </el-pagination>
      </div>
    </Panel>
    <el-dialog title="Download Contest Submissions"
               width="30%"
               :visible="downloadDialogVisible" @update:visible="downloadDialogVisible = $event">
      <el-switch v-model="excludeAdmin" active-text="Exclude admin submissions"></el-switch>
      <template #footer><span  class="dialog-footer">
        <el-button type="primary" @click="downloadSubmissions">确 定</el-button>
      </span></template>
    </el-dialog>
  </div>
</template>
<script>
  import api from '../../api.js'
  import utils from '@/utils/utils'
  import {CONTEST_STATUS_REVERSE} from '@/utils/constants'

  export default {
    name: 'ContestList',
    data () {
      return {
        pageSize: 10,
        total: 0,
        contestList: [],
        keyword: '',
        loading: false,
        excludeAdmin: true,
        currentPage: 1,
        currentId: 1,
        downloadDialogVisible: false
      }
    },
    mounted () {
      this.getContestList(this.currentPage)
    },
    filters: {
      contestStatus (value) {
        return CONTEST_STATUS_REVERSE[value].name
      }
    },
    methods: {
      // 切换页码回调
      currentChange (page) {
        this.currentPage = page
        this.getContestList(page)
      },
      getContestList (page) {
        this.loading = true
        api.getContestList((page - 1) * this.pageSize, this.pageSize, this.keyword).then(res => {
          this.loading = false
          this.total = res.data.data.total
          this.contestList = res.data.data.results
        }, res => {
          this.loading = false
        })
      },
      openDownloadOptions (contestId) {
        this.downloadDialogVisible = true
        this.currentId = contestId
      },
      downloadSubmissions () {
        let excludeAdmin = this.excludeAdmin ? '1' : '0'
        let url = `/admin/download_submissions?contest_id=${this.currentId}&exclude_admin=${excludeAdmin}`
        utils.downloadFile(url)
      },
      goEdit (contestId) {
        this.$router.push({name: 'edit-contest', params: {contestId}})
      },
      goContestAnnouncement (contestId) {
        this.$router.push({name: 'contest-announcement', params: {contestId}})
      },
      goContestProblemList (contestId) {
        this.$router.push({name: 'contest-problem-list', params: {contestId}})
      },
      handleVisibleSwitch (row) {
        api.editContest(row)
      }
    },
    watch: {
      'keyword' () {
        this.currentChange(1)
      }
    }
  }
</script>
