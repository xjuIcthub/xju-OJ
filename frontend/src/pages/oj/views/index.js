import NotFound from './general/404.vue'
import Home from './general/Home.vue'

const ProblemList = () => import('./problem/ProblemList.vue')
const Logout = () => import('./user/Logout.vue')
const UserHome = () => import('./user/UserHome.vue')
const About = () => import('./help/About.vue')
const FAQ = () => import('./help/FAQ.vue')
const Announcements = () => import('./general/Announcements.vue')

const SubmissionList = () => import('@oj/views/submission/SubmissionList.vue')
const SubmissionDetails = () => import('@oj/views/submission/SubmissionDetails.vue')

const ACMRank = () => import('@oj/views/rank/ACMRank.vue')
const OIRank = () => import('@oj/views/rank/OIRank.vue')

const ApplyResetPassword = () => import('@oj/views/user/ApplyResetPassword.vue')
const ResetPassword = () => import('@oj/views/user/ResetPassword.vue')

const Problem = () => import('@oj/views/problem/Problem.vue')

export {
  Home, NotFound, Announcements,
  Logout, UserHome, About, FAQ,
  ProblemList, Problem,
  ACMRank, OIRank,
  SubmissionList, SubmissionDetails,
  ApplyResetPassword, ResetPassword
}
/* 组件导出分为两类, 一类常用的直接导出，另一类诸如Login, Logout等用懒加载,懒加载不在此处导出
 *   在对应的route内加载
 *   见https://router.vuejs.org/en/advanced/lazy-loading.html
 */
