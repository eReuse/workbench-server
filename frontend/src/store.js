import Vue from 'vue'
import Vuex from 'vuex'

import axios from 'axios'

Vue.use(Vuex)

// const server = 'http://localhost:8090'
const server = 'http://192.168.2.2:8090'

const state = {
  plugged_usbs: {},
  withSimulator: true,
  simulator: {},
  inventories: [],
  flash: null
}

const mutations = {
  setPluggedUsbs (state, usbs) {
    state.plugged_usbs = usbs
  },
  setWithSimulator (state, data) {
    state.withSimulator = data
  },
  setSimulator (state, data) {
    state.simulator = data
  },
  setInventories (state, data) {
    data.sort(function (a, b) {
      return new Date(b['json']['created'] || b['json']['date']) - new Date(a['json']['created'] || a['json']['date'])
    })

    if (JSON.stringify(state.inventories) !== JSON.stringify(data)) {
      state.inventories = data
    }
  },
  setFlash (state, msg) {
    state.flash = msg
  }
}

const actions = {
  getPluggedUsbs (store) {
    axios.get(server + '/usbs').then(function (response) {
      if ('acknowledge' in response['data'] && response['data']['acknowledge']) {
        store.commit('setPluggedUsbs', response['data']['usbs'])
      }
    }).catch(function (error) {
      console.log(error)
    })
  },
  plugUsb (store, payload) {
    axios.get(server + '/add_usb', {params: {usb: payload['serial'], inventory: payload['inventory']}}).catch(function (error) {
      console.log(error)
    })
  },
  unplugUsb (store, payload) {
    axios.get(server + '/del_usb', {params: {inventory: payload}}).catch(function (error) {
      console.log(error)
    })
  },
  toggleSimulator (store) {
    store.commit('setWithSimulator', !store.getters.withSimulator)
  },
  getSimulator (store) {
    axios.get(server + '/simulated_inventories').then(function (response) {
      if ('acknowledge' in response['data'] && response['data']['acknowledge']) {
        store.commit('setSimulator', response['data']['data'])
      }
    }).catch(function (error) {
      console.log(error)
    })
  },
  getInventories (store) {
    axios.get(server + '/new_inventories').then(function (response) {
      if ('acknowledge' in response['data'] && response['data']['acknowledge']) {
        store.commit('setInventories', response['data']['inventories'])
      }
    }).catch(function (error) {
      console.log(error)
    })
  },
  Flash (store, msg) {
    store.commit('setFlash', msg)
    setInterval(function () {
      store.commit('setFlash', null)
    }, 10000)
  }
}

const getters = {
  flash (state) {
    return state.flash
  },
  plugged_usbs (state) {
    return state.plugged_usbs
  },
  withSimulator (state) {
    return state.withSimulator
  },
  simulations (state) {
    return state.simulator
  },
  inventories (state) {
    return state.inventories
  }
}

export default new Vuex.Store({
  state, mutations, actions, getters
})
