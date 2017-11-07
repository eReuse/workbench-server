function plug_usb(usb) {
	$.get("/add_usb", {"usb": usb.data("serial"), "inventory": usb.parents(".inventory:first").prop("id")});
}

function unplug_usb(usb) {
	$.get("/del_usb", {"inventory": usb.parents(".inventory:first").prop("id")});
}

function toggle_usbs(e) {
	var $this = $(this), usb = $this.parent(), serial = usb.data("serial"), icon = $this.children("i"), 
			this_on = $("[data-serial=" + serial + "] > a > i.fa-toggle-on"), deactivate_this = (this_on.length > 0)
			other_on = usb.siblings("li").find("a > i.fa-toggle-on"), deactivate_other = (other_on.length > 0);

	if(deactivate_this) {
		unplug_usb(this_on);
		this_on.toggleClass("fa-toggle-off fa-toggle-on");
	}

	if(deactivate_other) {
		unplug_usb(other_on);
		other_on.toggleClass("fa-toggle-off fa-toggle-on");
	}

	if(icon.hasClass("fa-toggle-off") && $this.parents(".inventory:first").prop("id") !== this_on.parents(".inventory:first").prop("id")) {
		plug_usb(usb);
		icon.toggleClass("fa-toggle-on fa-toggle-off");
	}

	e.preventDefault();
}

function toggle_timed(e) {
	var $this = $(this);
	$this.children("i").toggleClass("fa-hourglass-half fa-hourglass-o");

	e.preventDefault();
}

function launch_inventory(e) {
	var inventory = $(this).parents(".inventory:first"), timed = inventory.find(".timed > i").hasClass("fa-hourglass-half"), icon = $(this).children("i");
	var rocket = "fa-rocket", spinner = "fa-spin fa-spinner", ok = "fa-check text-success", fail = "fa-close text-danger";
	
	icon.removeClass(rocket);
	icon.addClass(spinner)
	$.post("/simulate_inventory", {"inventory": inventory.prop("id"), "timed": timed}).done(function() {
		icon.removeClass(spinner);
		icon.addClass(ok);
		setTimeout(function() {
			icon.removeClass(ok);
			icon.addClass(rocket)
		}, 3000);
	}).fail(function(jqXHR, textStatus, errorThrown) {
		icon.removeClass(spinner);
		icon.addClass(fail);
		setTimeout(function() {
			icon.removeClass(fail);
			icon.addClass(rocket)
		}, 3000);
	});

	e.preventDefault();
}

$(document).ready(function() {
	$(".plug").on("click", toggle_usbs);
	$(".launch").on("click", launch_inventory);
	$(".timed").on("click", toggle_timed);
});