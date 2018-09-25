# app = WorkbenchServer()
# You will need certificates if you want to serve through HTTPS
# To generate certificates see https://blog.miguelgrinberg.com/post/running-your-flask-application-over-https
# app.run('0.0.0.0', 8091, threaded=True)
from workbench_server.flaskapp import WorkbenchServer

app = WorkbenchServer()
