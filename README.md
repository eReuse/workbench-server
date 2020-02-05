# WorkbenchServer
Server for Workbench. WorkbenchServer exposes a REST API where
clients like Workbench and DeviceHub can interact to augment
snapshotting computers.

## Installation
1. Install the following dependencies:
   - python 3 with pip (Debian 9: `apt install python3-pip`)
   - Postgresql 9.6 or better (Debian 9: `apt install postgresql`)
   - If you want to process Androids:
     - adb (Debian 9: `apt install adb`)
     - Java (Debian 9: `apt install default-jre`)
   - If you want to print tags directly, cups (Debian 9: `apt install libcups2-dev`).
2. Clone WorkbenchServer:
   `git clone https://github.com/ereuse/workbench-server && cd workbench-server`.
3. Install WorkbenchServer: `pip3 install -e . -r requirements.txt`.
4. Execute the `examples/create-db.sh` scrpit, which creates the required database. 
    -  In Linux, execute the following two commands (adapt them to your distro):

      1. ``sudo su - postgres``.
      2. ``bash /home/{$USER}/workbench-server/examples/create-db.sh ws dhub``, and password
         ``ereuse``.

   -  In MacOS: ``bash examples/create-db.sh devicehub dhub``, and password
      ``ereuse``.

Run `examples/app.py` to run the server.

[Workbench](https://github.com/ereuse/workbench) is the main client for WorkbenchServer,
and you will need a [DeviceHubClient](https://github.com/ereuse/devicehubclient)
as a GUI client for WorkbenchServer.
