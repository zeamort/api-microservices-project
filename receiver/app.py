import connexion
from connexion import NoContent
import json
from datetime import datetime
import requests
import yaml
import logging
import logging.config
import uuid
from pykafka import KafkaClient
import time
import os

MAX_EVENTS = 5
EVENT_FILE = "events.json"

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

retry_count = 0
# Initialize KafkaClient with your Kafka server details
while (retry_count < app_config['max_retries']):
    logger.info("Attempting to connect to Kafka. Attempt #: %s", retry_count + 1)
    try:
        client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
        topic = client.topics[str.encode(app_config['events']['topic'])]
        producer = topic.get_sync_producer()
        logger.info("Successfully connected to Kafka on attempt #: %s", retry_count + 1)
        break
    except Exception as e:
        logger.error("Failed to connect to Kafka on attempt #:%s, error: %s", retry_count + 1, e)
        time.sleep(app_config['sleep_time'])
        retry_count += 1
else:
    logger.error("Exceeded maximum number of retries (%s) for Kafka connection", app_config['max_retries'])
    

#  Your functions here
def report_power_usage_reading(body):
    body['trace_id'] = str(uuid.uuid4())
    
    logger.info(f"Received event power-usage request with a trace id of {body['trace_id']}")

    # Construct the message
    msg = {
        "type": "power_usage",  # Your event type
        "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    logger.info(f"Produced power-usage event to Kafka (Id: {body['trace_id']})")

    return NoContent, 201


def report_location_reading(body):
    body['trace_id'] = str(uuid.uuid4())
    
    logger.info(f"Received event location request with a trace id of {body['trace_id']}")
    
    # Construct the message
    msg = {
        "type": "location",  # Your event type
        "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    logger.info(f"Produced location event to Kafka (Id: {body['trace_id']})")

    return NoContent, 201


def save_event(event_message, event_type):
    with open(EVENT_FILE, "r") as json_file:
        events = json.load(json_file)

    events[event_type]["count"] += 1

    # format the event message based on the event type
    if event_type == "power_usage":
        formatted_event_message = {
            "message_data": f"{event_message['device_type']} unit with device id {event_message['device_id']} outputted {event_message['power_data']['power_W']} watts of power and the battery is currently at {event_message['power_data']['state_of_charge_%']}%.",
            "received_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        }
    elif event_type == "location":
        formatted_event_message = {
            "message_data": f"{event_message['device_type']} unit with device id {event_message['device_id']} is currently located at {event_message['location_data']['gps_latitude']}, {event_message['location_data']['gps_longitude']}.",
            "received_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        }

    # insert the formatted event message at the beginning of the list of recent messages
    events[event_type]["recent"].insert(0, formatted_event_message)

    # check if the number of messages is now exceeding MAX_EVENTS, in which case remove the oldest message
    if len(events[event_type]["recent"]) > MAX_EVENTS:
        events[event_type]["recent"].pop()
    
    # write the updated events to the file
    with open(EVENT_FILE, "w") as json_file:
        json.dump(events, json_file)


def main():
    app = connexion.FlaskApp(__name__, specification_dir='')
    app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
    app.run(host='0.0.0.0', port=8080)


if __name__ == "__main__":
    main()
