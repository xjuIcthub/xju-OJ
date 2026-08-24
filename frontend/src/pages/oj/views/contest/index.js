const ContestList = () => import('./ContestList.vue')
const ContestDetails = () => import('./ContestDetail.vue')
const ContestProblemList = () => import('./children/ContestProblemList.vue')
const ContestRank = () => import('./children/ContestRank.vue')
const ACMContestHelper = () => import('./children/ACMHelper.vue')

export {ContestDetails, ContestList, ContestProblemList, ContestRank, ACMContestHelper}
