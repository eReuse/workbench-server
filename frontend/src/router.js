import Vue from 'vue'
import Router from 'vue-router'
import Inventories from '@/Inventories'
import Tag from '@/Tag'
import Config from '@/Config'

Vue.use(Router)

export default new Router({
  routes: [
    { path: '/', name: 'inventories', component: Inventories },
    { path: '/tag', name: 'tag', component: Tag },
    { path: '/config', name: 'config', component: Config }
  ]
})
