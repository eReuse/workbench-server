from configparser import ConfigParser

from flask import Response, jsonify, request


class Config:
    def __init__(self, app, config_ini) -> None:
        self.config_ini = config_ini
        app.add_url_rule('/config', view_func=self.view, methods=['GET', 'POST'])

    def view(self):
        if request.method == 'GET':
            data, *_ = self.read_config()
            return jsonify(data)
        else:  # POST
            data = request.get_json()
            _, sections, structure = self.read_config()
            self.write_config(data, sections, structure)
            return Response(status=201)

    def read_config(self):
        config = ConfigParser()
        config.read(self.config_ini)
        sections = ["DEFAULT"]
        sections.extend(config.sections())

        d = {}
        structure = {}
        for section in sections:
            structure[section] = []
            for key, value in config[section].items():
                key = key.upper()

                if section == "DEFAULT" or key not in structure["DEFAULT"]:
                    structure[section].append(key)

                if key == "_ID":
                    key = "ID_"
                elif key == "FLASK":
                    key = "SERVER"
                elif key == 'STEPS' or key == 'STRESS':
                    value = int(value)
                d[key] = value

        return d, sections, structure

    def write_config(self, data, sections, structure):
        config = ConfigParser()
        config.optionxform = str

        for section in sections:
            result = {}
            for key in structure[section]:
                if key == "_ID":
                    d_key = "ID_"
                elif key == "FLASK":
                    d_key = "SERVER"
                else:
                    d_key = key

                if key == 'STEPS' or key == 'STRESS':
                    value = str(data[d_key])
                else:
                    value = data[d_key]
                result[key] = value

            config[section] = result

        with open(self.config_ini, "w") as configfile:
            config.write(configfile)
