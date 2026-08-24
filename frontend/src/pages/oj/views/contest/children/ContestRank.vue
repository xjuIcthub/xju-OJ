<template>
  <div>
    <component :is="currentView"></component>
  </div>
</template>

<script>
  import { mapGetters } from '@/store/compat'
  import { types } from '../../../../../store'
  import ACMContestRank from './ACMContestRank.vue'
  import OIContestRank from './OIContestRank.vue'

  const NullComponent = {
    name: 'null-component',
    render: () => null
  }

  export default {
    name: 'contest-rank',
    components: {
      ACMContestRank,
      OIContestRank,
      NullComponent
    },
    computed: {
      ...mapGetters(['contestRuleType']),
      currentView () {
        if (this.contestRuleType === null) {
          return 'NullComponent'
        }
        return this.contestRuleType === 'ACM' ? 'ACMContestRank' : 'OIContestRank'
      }
    },
    beforeRouteLeave () {
      this.$store.commit(types.CHANGE_CONTEST_ITEM_VISIBLE, {menu: true})
    }
  }
</script>
<style lang="less" scoped>
</style>
