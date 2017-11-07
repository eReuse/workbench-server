from wtforms import Form, StringField, RadioField, TextAreaField, BooleanField
from wtforms.fields.html5 import IntegerField

from jinja2 import Template

from markupsafe import Markup

computer_types = [("Desktop", "Desktop"), ("Laptop", "Laptop"), ("Netbook", "Netbook"), ("Server", "Server"), ("Microtower", "Microtower")]
tipical_choices_4_config = [("no", "No"), ("yes", "Yes"), ("ask", "Ask")]
visual_grades = [("A", "Brand new device"), ("B", "Used, but no remarkable aesthetic defects"), ("C", "Light aesthetic defects (scratches, dents, decoloration)"),
								 ("D", "Serious aesthetic defects (cracked covers, broken parts)")]
functional_grades = [("A", "Brand new device"), ("B", "Used, but no remarkable functional defects"), ("C", "Light functional defects (soft noises, dead pixels, erased key labels)"),
										 ("D", "Serious functional defects (loud noises, annoying audio/video artifacts, missing keys)")]

class SwitcherWidget(object):
	tmpl = """
<div class="form-group{% if field.errors %} has-error{% endif %}{% if field.render_kw and 'group' in field.render_kw %} {{ field.render_kw['group'] }}{% endif %}">
  {{ field.label(class_ = "control-label") }}
  <div class="switch-toggle alert alert-light">
    {%- for subfield in field -%}
    	{%- if loop.index0 -%}
      	{{ subfield() }}
      {%- else  -%}
      	{{ subfield(checked = True) }}
      {%- endif -%}
      {{ subfield.label(onClick = "") }}
    {%- endfor -%}

    <a class="btn btn-primary"></a>
  </div>
  {%- if field.errors -%}
  	<div class="help-block">
  		<ul>
  			{%- for error in field.errors -%}
  				<li>{{ error }}</li>
  			{%- endfor -%}
  		</ul>
  	</div>
  {%- endif -%}
</div>
"""

	def __call__(self, field, **kwargs):
		t = Template(self.tmpl)
		return Markup(t.render(field = field, **kwargs))

class OnOffWidget(SwitcherWidget):
	tmpl = """
<div class="form-group{% if field.errors %} has-error{% endif %}{% if field.render_kw and 'group' in field.render_kw %} {{ field.render_kw['group'] }}{% endif %}">
  <label class="switch-light" onclick="">
  	<input type="checkbox" name="{{ field.name }}"{% if field.data %} checked="checked"{% endif %}>
  	<strong>
  		{{ field.label.text }}
  	</strong>

  	<span class="alert alert-light">
  		{%- for choice in field.choices -%}
  			<span>{{ choice }}</span>
  		{%- endfor -%}
  		<a class="btn btn-primary"></a>
  	</span>
  </label>
</div>
"""

class QRWidget(object):
	tmpl = """
<div class="form-group{% if field.errors %} has-error{% endif %}{% if field.render_kw and 'group' in field.render_kw %} {{ field.render_kw['group'] }}{% endif %}">
  {{ field.label(class_ = "form-label" ) }}
  <div class="input-group">
  	<input class="form-control qr-input" id="{{ field.name }}" name="{{ field.name }}" type="text" value="{{ field._value() }}">
  	<div class="input-group-addon"><i class="fa fa-qrcode"></i></div>
  </div>
</div>
<video id ="qr-preview-{{ field.name }}" class="qr-preview d-none"></video>
"""

	def __call__(self, field, **kwargs):
		t = Template(self.tmpl)
		return Markup(t.render(field = field, **kwargs))

class SwitcherField(RadioField):
	widget = SwitcherWidget()

class OnOffField(BooleanField):
	widget = OnOffWidget()

	def __init__(self, label=None, validators=None, **kwargs):
		self.choices = kwargs.pop("choices") if "choices" in kwargs else [("off", "Off"), ("on", "On")]
		super(OnOffField, self).__init__(label, validators, **kwargs)

class QRField(StringField):
	widget = QRWidget()

class ComputerForm(Form):
	id_ = QRField("System ID", render_kw = {"group": "col-xs-6"})
	gid = QRField("Giver ID", render_kw = {"group": "col-xs-6"})
	lot = StringField("Lot")
	device_type = SwitcherField("Device type", choices = computer_types)
	visual_grade = RadioField("Visual grade", choices = visual_grades)
	functional_grade = RadioField("Functional grade", choices = functional_grades)
	comment = TextAreaField("Comment")

class ConfigIniForm(Form):
	EQUIP = RadioField("Device type", choices = computer_types + [("ask", "Ask"), ("no", "Do not ask")], default = "no")
	PID = SwitcherField("PID", choices = tipical_choices_4_config, render_kw = {"group": "col-xs-6"})
	ID_ = SwitcherField("ID", choices = tipical_choices_4_config, render_kw = {"group": "col-xs-6"})
	LABEL = SwitcherField("Label", choices = tipical_choices_4_config, render_kw = {"group": "col-xs-6"})
	COMMENT = SwitcherField("Comment", choices = tipical_choices_4_config, render_kw = {"group": "col-xs-6"})
	VISUAL_GRADE = RadioField("Visual grade", choices = visual_grades + [("ask", "Ask"), ("no", "Do not ask")], default = "no")
	FUNCTIONAL_GRADE = RadioField("Functional grade", choices = functional_grades + [("ask", "Ask"), ("no", "Do not ask")], default = "no")
	COPY_TO_USB = OnOffField("Copy to USB", choices = ["No", "Yes"], false_values = ("no", "false",), render_kw = {"group": "col-xs-6"})
	SENDTOSERVER = OnOffField("Send to server", choices = ["No", "Yes"], false_values = ("no", "false",), render_kw = {"group": "col-xs-6"})
	SMART = RadioField("SMART test", choices = [("none", "Do not test"), ("short", "Short test"), ("long", "Long test")], default = "none")
	STRESS = IntegerField("Stress test", default = 0, render_kw = {"group": "col-xs-6"})
	SERVER = StringField("Server post phase URL", render_kw = {"group": "col-xs-6"})
	BROKER = StringField("Celery broker url", render_kw = {"group": "col-xs-6"})
	QUEUE = StringField("Celery queue", render_kw = {"group": "col-xs-6"})
	ERASE = SwitcherField("Erase disk", choices = tipical_choices_4_config, render_kw = {"group": "col-xs-6"})
	MODE = OnOffField("Erase mode", choices = ["Basic", "Secure"], false_values = ("no", "false", "EraseBasic"), render_kw = {"group": "col-xs-6"})
	STEPS = IntegerField("Erase iterations", default = 1, render_kw = {"group": "col-xs-6"})
	ZEROS = OnOffField("Overwrite with zeros", choices = ["No", "Yes"], false_values = ("no", "false",))
	DEBUG = OnOffField("Debug mode", choices = ["No", "Yes"], false_values = ("no", "false",), render_kw = {"group": "col-xs-6"})
	SIGN_OUTPUT = OnOffField("Sign the inventory", choices = ["No", "Yes"], false_values = ("no", "false",))
	INSTALL = SwitcherField("Install system image", choices = tipical_choices_4_config, render_kw = {"group": "col-xs-6"})
	IMAGE_NAME = StringField("Image name", render_kw = {"group": "col-xs-6"})
	IMAGE_DIR = StringField("Images folder")
	KEYBOARD_LAYOUT = StringField("Keyboard layout")
