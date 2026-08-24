import { createRouter, createWebHistory } from 'vue-router'
import routes from './routes'
import storage from '@/utils/storage'
import { STORAGE_KEY } from '@/utils/constants'
import store, { types, setStoreRouter } from '@/store'

const router = createRouter({
  history: createWebHistory('/'),
  scrollBehavior (to, from, savedPosition) { return savedPosition || { left: 0, top: 0 } },
  routes
})
setStoreRouter(router)

router.beforeEach(to => {
  if (to.matched.some(record => record.meta.requiresAuth) && !storage.get(STORAGE_KEY.AUTHED)) {
    store.commit(types.CHANGE_MODAL_STATUS, { mode: 'login', visible: true })
    return { name: 'home' }
  }
})

export default router
