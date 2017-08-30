// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from 'vue'
import App from '@/App'

import store from '@/store'
import router from '@/router'

import moment from 'moment'

import 'bootstrap/dist/css/bootstrap.css'
import 'font-awesome/css/font-awesome.css'

import Usbs from '@/components/usbs'
import Simulator from '@/components/simulator'
import Inventories from '@/components/inventories'

Vue.config.productionTip = false

Vue.component('usbs', Usbs)
Vue.component('simulator', Simulator)
Vue.component('inventories', Inventories)

Vue.mixin({
  methods: {
    deviceIcon (type) {
      return {
        'Desktop': 'fa-desktop',
        'Laptop': 'fa-laptop',
        'Netbook': 'fa-laptop netbook',
        'Server': 'fa-server',
        'Microtower': 'fa-building-o'
      }[type] || 'fa-question'
    }
  }
})

Vue.filter('moment', function (value, format) {
  if (typeof format === 'undefined') {
    format = 'LLLL'
  }

  return moment(value).format(format)
})

/* eslint-disable no-new */
new Vue({
  el: '#app',
  store,
  router,
  template: '<App/>',
  components: { App },
  methods: {
    refreshData () {
      this.$store.dispatch('getPluggedUsbs')
      this.$store.dispatch('getInventories')
    }
  },
  mounted () {
    this.refreshData()
    setInterval(this.refreshData, 5000)
    this.$store.dispatch('getSimulator')
  }
})
