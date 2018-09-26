# WorkbenchServer
Server for Workbench. WorkbenchServer exposes a REST API where
clients like Workbench and DeviceHub can interact to augment
snapshotting computers.

## Installation
1. Install python3 with pip (in Debian 9 is `apt install python3-pip`).
2. If you want to use pycups in Debian 9, install `apt install libcups2-dev`.
3. Clone WorkbenchServer:
   `git clone https://github.com/ereuse/workbench-server && cd workbench-server`.
4. Install WorkbenchServer: `pip3 install -e . -r requirements.txt`.

[Workbench](https://github.com/ereuse/workbench) is the main client for WorkbenchServer,
and you will need a [DeviceHubClient](https://github.com/ereuse/devicehubclient)
as a GUI client for WorkbenchServer.

In Debian, you will need to set an *udeb* rule in order to be able to read USB information without
granting root permissions to WorkbenchServer. Perform as follows with *root*, where `user-group`
is the group where the user executing WorkbenchServer is: 
`echo '﻿SUBSYSTEM=="usb", MODE="0666", GROUP="user-group"' > /etc/udev/rules.d/99-workbench.rules`
and reboot.

## Testing
### An app.py
```python
from pathlib import Path

from workbench_server.flaskapp import WorkbenchServer

app = WorkbenchServer()
# You will need certificates if you want to serve through HTTPS
# To generate certificates see https://blog.miguelgrinberg.com/post/running-your-flask-application-over-https
directory = Path(__file__).parent
ssl = str(directory.joinpath('cert.pem')), str(directory.joinpath('key.pem'))
app.run('0.0.0.0', 8091, threaded=True, ssl_context=ssl, use_reloader=False)
```
