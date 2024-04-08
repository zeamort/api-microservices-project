import connexion
from connexion import NoContent
import yaml
import logging
import logging.config
import json
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
import os

if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

# Load the app_conf.yml configuration 
with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())

# Load the log_conf.yml configuration 
with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

# Create a logger for this file
logger = logging.getLogger('basicLogger')

logger.info("App Conf File: %s" % app_conf_file)
logger.info("Log Conf File: %s" % log_conf_file)

def get_power_usage_reading(index):
    """ Get Power Usage Reading in History """
    return get_event_reading_by_type(index, "power_usage")

def get_location_reading(index):
    """ Get Location Reading in History """
    return get_event_reading_by_type(index, "location")

def get_event_reading_by_type(index, event_type):
    """ General function to retrieve event reading by type and index """
    hostname = "%s:%d" % (app_config["events"]["hostname"], app_config["events"]["port"])
    client = KafkaClient(hosts=hostname)
    topic = client.topics[str.encode(app_config["events"]["topic"])]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)

    logger.info("Retrieving %s at index %d", event_type, index)
    current_index = 0
    try:
        for message in consumer:
            if message is not None and message.value is not None:
                msg_str = message.value.decode('utf-8')
                msg = json.loads(msg_str)

                if msg["type"] == event_type:
                    if current_index == index:
                        logger.info("Found %s at index %d", event_type, index)
                        return msg, 200
                    current_index += 1

    except Exception as e:
        logger.error("Error retrieving message: %s", str(e))

    logger.error("Could not find %s at index %d", event_type, index)
    return {"message": "Not Found"}, 404

def main():
    app = connexion.FlaskApp(__name__, specification_dir='')
    app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
    app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.run(host='0.0.0.0', port=8110)

if __name__ == "__main__":
    main()
