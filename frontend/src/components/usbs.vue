<template>
  <div class="plugged-usbs">
    <h3>Plugged usbs</h3>
    <ul class="list-unstyled">
        <li class="media" v-for="(usb, inventory) in usbs" key="inventory">
          <div class="text-center align-self-center">
            <div class="usb-icon"><i class="fa fa-usb fa-2x"></i></div>
            <div class="unplug-icon"><a href="#" @click.prevent="unplugMe(inventory, $event)"><i class="fa fa-toggle-on"></i></a></div>
          </div>
          <div class="media-body">
            <h5>{{ usb['vendor'] }} {{ usb['product'] }}</h5>
            <div>{{ usb['usb'] }}</div>
            <div>{{ inventory }}</div>
          </div>
        </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'usbs',
  methods: {
    unplugMe (inventory, e) {
      // e.target.closest('.media').classList.add('disabled')
      // e.target.parentElement.removeChild(e.target)

      this.$store.dispatch('unplugUsb', inventory)
    }
  },
  computed: {
    usbs () {
      return this.$store.getters.plugged_usbs
    }
  }
}
</script>

<style scoped>
  .disabled {
    color: gray;
  }
</style>
