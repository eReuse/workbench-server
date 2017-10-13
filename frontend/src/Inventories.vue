<template>
  <div id="app" class="container-fluid">
    <h1>
      eReuse's Workbench GUI
      <small class="pull-right">
        <router-link :to="{ name: 'config' }"><i class="fa fa-gear"></i></router-link>
      </small>
    </h1>
    <div v-if="flash" class="alert" :class="'alert-' + flash['severity']" role="alert">
      {{ flash['msg'] }}
    </div>
    <div class="row">
      <usbs class="col-xs-12 col-md-12"></usbs>
    </div>
    <div class="row">
      <inventories class="col-xs-12 col-md-12"></inventories>
    </div>
  </div>
</template>

<script>
export default {
  name: 'app',
  computed: {
    flash () {
      return this.$store.getters.flash
    }
  }
}
</script>
