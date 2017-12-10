"""
Main worker file when executing through a service
"""
from workbench_server.scripts import dummy
from workbench_server.worker import Worker

dummy(Worker(host='localhost', json_path='~/Documents/json'), timing=1, add_usb=True, remove_usb=False,
      install_os=False)
