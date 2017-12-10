# WorkbenchServer
Manage Workbench execution in business environments.

## Installation
1. Install python3 with pip (in Debian 9 is `apt install python3-pip`).
2. Install lib-usb or openUSB (in Debian 9 is `apt install libusb-1.0-0`)
3. Clone WorkbenchServer: `git clone https://github.com/ereuse/workbench-server && cd workbench-server`.
4. Install WorkbenchServer: `pip3 install -e . -r requirements.txt`.

You will probably want to install the WorkbenchServerClient to be able to manage
WorkbenchServer in an easy way.

In Debian, you will need to set an *udeb* rule in order to be able to read USB information without granting
root permissions to WorkbenchServer. Perform as follows with *root*, where `user-group` is the group where the user
executing WorkbenchServer is: 
`echo '﻿SUBSYSTEM=="usb", MODE="0666", GROUP="user-group"' > /etc/udev/rules.d/99-workbench.rules` and reboot.

## Testing

### An app.py
```python
from os import path
from shutil import copyfile

from workbench_server.web_service.flaskapp import WorkbenchWebService

# Copy config.ini to a temp so we can modify it
directory = path.abspath(path.dirname(__file__))
original_config_ini = path.join(directory, 'workbench_server', 'tests', 'fixtures', 'config.ini')
tmp_config_ini = path.join('/tmp', 'workbench_server_run_config.ini')
copyfile(original_config_ini, tmp_config_ini)
app = WorkbenchWebService(__name__, config_ini=tmp_config_ini, json_path='~/Documents/json')
# We can use a certificate so we don't get Mixed content
# To generate certificates see https://blog.miguelgrinberg.com/post/running-your-flask-application-over-https
# If you don't want to generate certificates, delete the `ssl_context` param: 
app.run('0.0.0.0', 8091, debug=True, ssl_context=(path.join(directory, 'cert.pem'), path.join(directory, 'key.pem')))
```

### Create dummy connections
```python
"""
Main worker file when executing through a service
"""
from workbench_server.web_service.scripts.dummy import dummy
from workbench_server.worker import Worker

dummy(Worker(host='localhost', json_path='~/Documents/json'), timing=1, add_usb=True, remove_usb=False, install_os=False)
```