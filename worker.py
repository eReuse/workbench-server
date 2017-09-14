from datetime import timedelta

from json import dumps, loads

from celery import Celery
# from celery.utils.log import get_task_logger

from redis import StrictRedis

from dateutil.parser import parse

# serverIP = "192.168.99.100"
# serverIP = "localhost"
# serverIP = "redis"
serverIP = "192.168.2.2"
redisBroker = "redis://{}:6379/0".format(serverIP)

queue = Celery("workbench", broker = redisBroker)
queue.conf.update(worker_pool_restarts=True)
redis = StrictRedis(host = serverIP, db = 1)
redis_usb = StrictRedis(host = serverIP, db = 2)
redis_consolidated = StrictRedis(host = serverIP, db = 3)

json_path = "./jsons"

# log = get_task_logger(__name__)

@queue.task
def consume_phase(json):
  if(isinstance(json, str)):
    json = loads(json)

  _uuid = json["_uuid"]

  aggregated_json = redis.get(_uuid)
  if aggregated_json is not None:
    aggregated_json = loads(str(aggregated_json, "utf-8"))

  if aggregated_json is None:
    aggregated_json = json
    aggregated_json["times"] = {"detection": json["created"]}
  elif "components" in json:
    aggregated_json["times"]["hd_benchmark"] = json["created"]
  elif "localpath" in json:
    aggregated_json["times"]["save_json"] = json["created"]
    aggregated_json["save_json"] = {"localpath": json["localpath"], "filename": json["filename"], "signed_data": json["signed_data"]}
  elif "copy_to_usb" in json:
    aggregated_json["times"]["copy_to_usb"] = json["created"]
  elif "stress_test_ok" in json:
    if "tests" not in aggregated_json:
      aggregated_json["tests"] = []
    aggregated_json["times"]["hd_stress_test"] = json["created"]
    aggregated_json["tests"].append({"@type": "StressTest", "success": json["stress_test_ok"], "elapsed": str(timedelta(minutes = json["stress_test_mins"]))})
  elif "install_image_ok" in json:
    elapsed = str(parse(json["created"]) - parse(aggregated_json["times"]["hd_stress_test"])).split(".")[0]
    aggregated_json["times"]["iso"] = json["created"]
    aggregated_json["osInstallation"] = {"label": json["image_name"], "success": json["install_image_ok"], "elapsed": elapsed}

  redis.set(_uuid, dumps(aggregated_json))

  if len(aggregated_json["times"].keys()) > 5 and "condition" in aggregated_json:
    consolidate_json(aggregated_json)

def consolidate_json(json):
  json["date"] = parse(json["created"]).replace(microsecond = 0).isoformat()
  del json["created"]

  json["snapshotSoftware"] = "Workbench"

  json["inventory"] = {"elapsed": str(parse(json["times"]["iso"]) - parse(json["times"]["detection"])).split(".")[0]}

  del json["times"]

  dumped = None
  if "save_json" in json:
    filename = json["save_json"]["filename"]
    del json["save_json"]

    dumped = dumps(json)
    with open("{}/{}".format(json_path, filename), "w") as f:
      f.write(dumped)

  redis.delete(json["_uuid"])
  redis_consolidated.set(json["_uuid"], dumped or dumps(json))

@queue.task
def add_usb(usb):
  inventory = usb.pop("inventory")
  redis_usb.set(inventory, dumps(usb))

@queue.task
def del_usb(usb):
  redis_usb.delete(usb["inventory"])

@queue.task
def tag_computer(json):
  _uuid = json["_uuid"]
  aggregated_json = redis.get(_uuid)
  if aggregated_json is not None:
    aggregated_json = loads(aggregated_json)

    if "label" in json and json["label"]:
      aggregated_json["label"] = json["label"]
    if "pid" in json and json["pid"]:
      aggregated_json["pid"] = json["pid"]
    if "_id" in json and json["_id"]:
      aggregated_json["_id"] = json["_id"]

    aggregated_json["device"]["type"] = json["device_type"]
    aggregated_json["condition"] = {"appearance": {"general": json["visual_grade"]}, "functionality": {"general": json["functional_grade"]}}

    if json["comment"]:
      aggregated_json["comment"] = json["comment"]

    redis.set(_uuid, dumps(aggregated_json))

    if len(aggregated_json["times"].keys()) > 5:
      consolidate_json(aggregated_json)
