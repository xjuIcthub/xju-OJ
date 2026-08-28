<template>
  <Panel shadow :padding="10">
    <template #title><div class="announcement-heading">
      <strong>{{title}}</strong>
      <button v-if="listVisible"
              type="button"
              class="announcement-action"
              :disabled="btnLoading"
              @click="init">
        <Icon type="refresh" :class="{ 'is-spinning': btnLoading }" />
        <span>{{$t('m.Refresh')}}</span>
      </button>
      <button v-else type="button" class="announcement-action" @click="goBack">
        <Icon type="undo" />
        <span>{{$t('m.Back')}}</span>
      </button>
    </div></template>

    <transition-group name="announcement-animate">
      <div class="no-announcement" v-if="!announcements.length" key="no-announcement">
        <p>{{$t('m.No_Announcements')}}</p>
      </div>
      <template v-if="listVisible">
        <ul class="announcements-container" key="list">
          <li v-for="announcement in announcements" :key="announcement.title">
            <div class="flex-container">
              <div class="title"><a class="entry" @click="goAnnouncement(announcement)">
                {{announcement.title}}</a></div>
              <div class="date">{{ $filters.localtime(announcement.create_time) }}</div>
              <div class="creator"> {{$t('m.By')}} {{announcement.created_by.username}}</div>
            </div>
          </li>
        </ul>
        <Pagination v-if="!isContest"
                    key="page"
                    :total="total"
                    :page-size="limit"
                    @on-change="getAnnouncementList">
        </Pagination>
      </template>

      <template v-else>
        <div v-katex v-html="announcement.content" key="content" class="content-container markdown-body"></div>
      </template>
    </transition-group>
  </Panel>
</template>
<script>
  import api from '@oj/api'
  import Pagination from '@oj/components/Pagination'

  export default {
    name: 'Announcement',
    components: {
      Pagination
    },
    data () {
      return {
        limit: 10,
        total: 10,
        btnLoading: false,
        announcements: [],
        announcement: '',
        listVisible: true
      }
    },
    mounted () {
      this.init()
    },
    methods: {
      init () {
        if (this.isContest) {
          this.getContestAnnouncementList()
        } else {
          this.getAnnouncementList()
        }
      },
      getAnnouncementList (page = 1) {
        this.btnLoading = true
        api.getAnnouncementList((page - 1) * this.limit, this.limit).then(res => {
          this.btnLoading = false
          this.announcements = res.data.data.results
          this.total = res.data.data.total
        }, () => {
          this.btnLoading = false
        })
      },
      getContestAnnouncementList () {
        this.btnLoading = true
        api.getContestAnnouncementList(this.$route.params.contestID).then(res => {
          this.btnLoading = false
          this.announcements = res.data.data
        }, () => {
          this.btnLoading = false
        })
      },
      goAnnouncement (announcement) {
        this.announcement = announcement
        this.listVisible = false
      },
      goBack () {
        this.listVisible = true
        this.announcement = ''
      }
    },
    computed: {
      title () {
        if (this.listVisible) {
          return this.isContest ? this.$t('m.Contest_Announcements') : this.$t('m.Announcements')
        } else {
          return this.announcement.title
        }
      },
      isContest () {
        return !!this.$route.params.contestID
      }
    }
  }
</script>

<style scoped lang="less">
  .announcement-heading { display: flex; width: 100%; align-items: center; justify-content: space-between; gap: 18px; }
  .announcement-heading > strong { min-width: 0; overflow: hidden; font-family: var(--font-serif); font-size: 21px; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }
  .announcement-action {
    display: inline-flex;
    min-width: 88px;
    height: 34px;
    align-items: center;
    justify-content: center;
    gap: 7px;
    padding: 0 11px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-bg);
    color: var(--color-text-muted);
    font: inherit;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: color var(--transition), border-color var(--transition), background-color var(--transition), transform var(--transition);
  }
  .announcement-action:hover:not(:disabled), .announcement-action:focus-visible:not(:disabled) { border-color: var(--line-strong); background: var(--color-bg-subtle); color: var(--color-text); }
  .announcement-action:active:not(:disabled) { transform: translateY(1px); }
  .announcement-action:disabled { cursor: wait; opacity: .58; }
  .announcement-action :deep(.legacy-icon) { display: inline-flex; align-items: center; justify-content: center; line-height: 0; }
  .announcement-action :deep(svg) { display: block; width: 14px; height: 14px; }
  .announcement-action .is-spinning { animation: announcement-refresh-spin 900ms linear infinite; }

  @keyframes announcement-refresh-spin { to { transform: rotate(360deg); } }

  .announcements-container {
    margin-top: -10px;
    margin-bottom: 10px;
    padding-left: 0;
    li {
      padding-top: 15px;
      list-style: none;
      padding-bottom: 15px;
      margin-left: 20px;
      font-size: 16px;
      border-bottom: 1px solid var(--color-border);
      &:last-child {
        border-bottom: none;
      }
      .flex-container {
        .title {
          flex: 1 1;
          text-align: left;
          padding-left: 10px;
          a.entry {
            color: var(--color-text);
            &:hover {
              color: var(--color-link);
              border-bottom: 1px solid var(--color-link);
            }
          }
        }
        .creator {
          flex: none;
          width: 200px;
          text-align: center;
        }
        .date {
          flex: none;
          width: 200px;
          text-align: center;
        }
      }
    }
  }

  .content-container {
    padding: 0 20px 20px 20px;
  }

  .no-announcement {
    text-align: center;
    font-size: 16px;
  }

  .announcement-animate-enter-active {
    animation: fadeIn 1s;
  }

  @media (prefers-reduced-motion: reduce) {
    .announcement-action, .announcement-action .is-spinning { transition: none; animation: none; }
  }
</style>
