<template>
  <div class="inventories">
    <h3>Inventories</h3>
    <table class="table table-responsive">
      <thead>
        <tr>
          <th><i class="fa fa-usb"></i></th>
          <th>Created</th>
          <th>Device</th>
          <th>Identification</th>
          <th>Grades</th>
          <th>Phases</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="(inventory, index) in inventories">
          <tr v-if="renderHeader(index)">
            <th colspan="6" class="text-center">
              {{ (inventory["json"]["created"] || inventory["json"]["date"]) | moment("LL") }}
            </th>
          </tr>
          <tr>
            <td v-if="hasPlugged(inventory['id'])">
              <router-link :to="{ name: 'tag', params: { inventory: inventory['id'], serial: plugged_usbs[inventory['id']]['usb']} }">
              <!-- a href="#" @click.prevent="tag_computer(inventory['id'], plugged_usbs[inventory['id']]['usb'])" -->
                <div>{{ plugged_usbs[inventory["id"]]["vendor"] }}</div>
                <div>{{ plugged_usbs[inventory["id"]]["product"] }}</div>
              <!-- /a -->
              </router-link>
            </td>
            <td v-else>&nbsp;</td>
            <td>
              {{ (inventory["json"]["created"] || inventory["json"]["date"]) | moment("HH:mm:ss") }}
              <i class="fa fa-info" :alt="inventory['id']" :title="inventory['id']"></i>
            </td>
            <td>
              <i class="fa" :class="deviceIcon(inventory['json']['device']['type'])"></i>
              {{ inventory["json"]["device"]["manufacturer"] }} {{ inventory["json"]["device"]["model"] }}
            </td>
            <td>{{ getIdentification(inventory["json"]) }}</td>
            <td>
              <template v-if="hasGrades(inventory['json'])">
                <i class="fa fa-eye"></i> 
                {{ inventory["json"]["condition"]["appearance"]["general"] }}
                <i class="fa fa-wrench"></i>
                {{ inventory["json"]["condition"]["functionality"]["general"] }}
              </template>
              <template v-else>Not rated</template>
            </td>
            <td class="text-center" :class="phaseClass(inventory['json'])" v-html="getStatusIcon(inventory['json'])"></td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>  
</template>

<script>
export default {
  name: 'inventories',
  methods: {
    renderHeader (index) {
      if (index === 0) {
        return true
      } else {
        var previousDate = new Date(this.inventories[index - 1].json['created'] || this.inventories[index - 1].json['date'])
        var currentDate = new Date(this.inventories[index].json['created'] || this.inventories[index].json['date'])
        previousDate.setHours(0, 0, 0, 0)
        currentDate.setHours(0, 0, 0, 0)

        return (currentDate.valueOf() !== previousDate.valueOf())
      }
    },
    hasPlugged (inventory) {
      return (inventory in this.plugged_usbs)
    },
    getIdentification (json) {
      var ident = []

      if ('label' in json) {
        ident.push(json['label'])
      }

      if ('pid' in json) {
        ident.push(json['pid'])
      }

      if ('_id' in json) {
        ident.push(json['_id'])
      }

      return ident.join(' - ') || 'Not identified'
    },
    hasGrades (json) {
      return 'condition' in json
    },
    getStatus (json) {
      if ('date' in json) {
        return ('uploaded' in json) ? 'Uploaded' : 'Finished'
      } else if ('iso' in json['times']) {
        return 'Not rated'
      } else {
        return 'Not finished'
      }
    },
    phaseClass (json) {
      return {
        'Not finished': 'bg-danger',
        'Not rated': 'bg-warning',
        'Finished': 'bg-info',
        'Uploaded': 'bg-success'
      }[this.getStatus(json)]
    },
    getStatusIcon (json) {
      var status = this.getStatus(json)
      if (status === 'Uploaded') {
        return '<i class="fa fa-cloud-upload"></i>'
      } else if (status === 'Finished') {
        return '<i class="fa fa-check"></i>'
      } else {
        return Object.keys(json['times']).length
      }
    },
    tag_computer (inventory, serial) {
      // var $modal = $('#modal')
      // var usb = this.plugged_usbs[inventory]

      // $modal.on('show.bs.modal', function (e) {
      //   $modal.find('.modal-title')
      //         .html('Tag computer on <small>' + inventory + '</small> with ' + usb['vendor'] + ' ' + usb['product'] + ' <small>' + serial + '</small>')

      //   $.get('/tag_computer_form').then(function (data) {
      //     $modal.find('.modal-body').html(data)
      //     // $('.fa-qrcod').parent().on('click', toggleQRscanner)
      //   })

      //   $modal.find('.modal-footer .btn-primary')
      //         .html('Tag it')
      //         .on('click', function () {
      //           $.post('/tag_computer', $modal.find('form').serialize())
      //             .fail(function (jqXHR, textStatus, errorThrown) {
      //               $modal.find('.modal-body').html(errorThrown)
      //             })
      //         })
      // }).modal('show')
    }
  },
  computed: {
    fields () {
      return {
        usb: {label: '<i class="fa fa-usb"></i>'},
        created: {label: 'Created'},
        device: {label: 'Device'},
        identification: {label: 'Identification'},
        grades: {label: 'Grades'},
        phases: {label: 'Phases'}
      }
    },
    inventories () {
      return this.$store.getters.inventories
    },
    plugged_usbs () {
      return this.$store.getters.plugged_usbs
    }
  }
}
</script>
