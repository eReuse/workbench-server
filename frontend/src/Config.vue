<template>
  <div id="app" class="container-fluid">
    <h1>
      <small><router-link :to="{ name: 'inventories' }"><i class="fa fa-arrow-left"></i></router-link></small>
      eReuse's Workbench configuration
    </h1>
    <div v-html="html"></div>
    <button class="btn btn-primary" type="button" @click="edit_config">Edit configuration</button>
  </div>
</template>

<script>
import axios from 'axios'

import 'css-toggle-switch/dist/toggle-switch.css'

// const server = 'http://localhost:8090'
const server = 'http://192.168.2.2:8090'

export default {
  name: 'config',
  data () {
    return { html: '' }
  },
  methods: {
    edit_config () {
      var form = document.getElementsByTagName('form')[0]
      var values = new FormData()

      for (var i = 0; i < form.elements.length; i++) {
        if (form.elements[i].type === 'radio') {
          if (form.elements[i].checked === true) {
            values.append(form.elements[i].name, form.elements[i].value)
          }
        } else if (form.elements[i].type === 'checkbox') {
          values.append(form.elements[i].name, form.elements[i].checked)
        } else {
          values.append(form.elements[i].name, form.elements[i].value)
        }
      }

      axios.post(server + '/edit_config_form', values).then(function (response) {
        this.$store.dispatch('Flash', {'msg': response.data.msg, 'severity': 'success'})
        this.$router.push({name: 'inventories'})
      }.bind(this)).catch(function (error) {
        this.html = error.response.data
      }.bind(this))
    }
  },
  beforeMount () {
    axios.get(server + '/edit_config_form').then(function (request) {
      this.html = request.data
    }.bind(this))
  }
}
</script>