from workbench_server.db import db
from workbench_server.flaskapp import WorkbenchServer
from workbench_server.log import log

log()
app = WorkbenchServer()
with app.app_context():
    db.create_all()
app.init_manager()
