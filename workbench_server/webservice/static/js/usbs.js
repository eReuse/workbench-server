function get_usbs() {
	$.get("/usbs").done(function(data) {
		var listed = Object.keys(data["usbs"]);

		$(".plugged_usbs .usb").map(function() {
			var $this = $(this);

			if(listed.indexOf($this.attr("id")) < 0) {
				$this.remove();
			}
		});

		var actual = $(".plugged_usbs .usb").map(function() { return $(this).prop("id"); }).get();

		listed.forEach(function(el) {
			if(actual.indexOf(el) < 0) {
				var tmpl = '<div id="{{ key }}" class="media usb"><div class="media-left media-middle"><i class="fa fa-usb fa-2x"></i></div><div class="media-body"><h4 class="media-heading">{{ vendor }} {{ product }}</h4><div>{{ usb }}</div><div>{{ key }}</div></div></div>';
				$(tmpl.replace(/{{ key }}/g, el).replace("{{ vendor }}", data["usbs"][el]["vendor"]).replace("{{ product }}", data["usbs"][el]["product"]).replace("{{ usb }}", data["usbs"][el]["usb"])).appendTo(".plugged_usbs");
			}
		})
	}).fail(function(jqXHR, textStatus, errorThrown) {
		console.log(jqXHR);
		console.log(textStatus);
		console.log(errorThrown);
	});

	setTimeout(get_usbs, 5000);
}

function manage() {
	usbs = get_usbs();
}

$(document).ready(function() {
	setTimeout(get_usbs, 5000);
});