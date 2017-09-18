<template>
  <div class="simulator">
    <h3>
      Simulator
      <small>
        <a href="#" @click.prevent="toggleMe">
          <i class="fa" :class="visible ? 'fa-toggle-on' : 'fa-toggle-off'"></i>
        </a>
      </small>
    </h3>
    <ul class="list-unstyled" v-if="visible">
      <li class="media" v-for="(data, inventory) in simulations['inventories']" key="inventory">
        <div class="text-center align-self-center launcher">
          <div class="rocket-icon">
            <a href="#" @click.prevent="launchInventory(inventory, $event)"><i class="fa fa-rocket fa-2x"></i></a>
          </div>
          <div class="timed-icon">
            <a href="#" @click.prevent="toggleTimed"><i class="fa fa-hourglass-half"></i></a>
          </div>
        </div>
        <div class="media-body">
          <h5>
            <i class="fa" :class="deviceIcon(data[0]['device']['type'])"></i>
            {{ data[0]["device"]["manufacturer"] }} {{ data[0]["device"]["model"] }}
            <small>{{ inventory }}</small>
          </h5>
          <div class="usb" v-for="(usb, serial) in simulations['usbs']" key="serial">
            <i class="fa fa-usb"></i> 
            {{ usb["vendor"] }} {{ usb["product"] }} <small>{{ serial }}</small>
            <a href="#" @click.prevent="toggleUsb(inventory, serial, $event)">
              <i class="fa" :class="isPlugged(inventory, serial) ? 'fa-toggle-on' : 'fa-toggle-off'"></i>
            </a>
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>

<script>
import axios from 'axios'

const server = process.env.SERVER_URL || 'http://localhost:8090'

export default {
  name: 'simulator',
  methods: {
    isPlugged (inventory, serial) {
      var plugged = this.$store.getters.plugged_usbs
      return (inventory in plugged && plugged[inventory]['usb'] === serial)
    },
    toggleMe () {
      this.$store.dispatch('toggleSimulator')
    },
    toggleUsb (inventory, serial, e) {
      e.target.classList.remove('fa-toggle-off', 'fa-toggle-on')
      e.target.classList.add('fa-spinner', 'fa-pulse')
      if (inventory in this.$store.getters.plugged_usbs) {
        this.$store.dispatch('unplugUsb', {inventory: inventory})
      } else {
        this.$store.dispatch('plugUsb', {inventory: inventory, serial: serial})
      }
    },
    toggleTimed (e) {
      if (e.target.classList.contains('fa-hourglass-half')) {
        e.target.classList.remove('fa-hourglass-half')
        e.target.classList.add('fa-hourglass-o')
      } else {
        e.target.classList.remove('fa-hourglass-o')
        e.target.classList.add('fa-hourglass-half')
      }
    },
    launchInventory (inventory, e) {
      var rocket = e.target
      var timed = e.target.closest('.launcher').querySelector('.timed-icon i')
      rocket.classList.remove('fa-rocket')
      rocket.classList.add('fa-spinner', 'fa-pulse')
      var args = {params: {inventory: inventory}}
      if (timed.classList.contains('fa-hourglass-half')) {
        args['params']['timed'] = true
      }
      axios.get(server + '/simulate_inventory', args).then(function () {
        rocket.classList.remove('fa-spinner', 'fa-pulse')
        rocket.classList.add('fa-check')
        setInterval(function () {
          rocket.classList.remove('fa-check')
          rocket.classList.add('fa-rocket')
        }, 5000)
      }).catch(function (error) {
        console.log(error)
      })
    }
  },
  computed: {
    simulations () {
      console.log(process.env)
      return this.$store.getters.simulations
    },
    visible () {
      return this.$store.getters.withSimulator
    }
  }
}
</script>