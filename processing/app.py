import connexion
from connexion import NoContent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from base import Base
from stats import Statistics
import datetime
import requests
from apscheduler.schedulers.background import BackgroundScheduler
import yaml
import logging
import logging.config
import numpy as np
import copy
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
import os
import json
from pykafka import KafkaClient
import time


if "TARGET_ENV" not in os.environ or os.environ["TARGET_ENV"] != "test":
    CORS(app.app)
    app.app.config['CORS_HEADERS'] = 'Content-Type'

if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yaml"
    log_conf_file = "/config/log_conf.yaml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yaml"
    log_conf_file = "log_conf.yaml"

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

# Create the database connection
DB_ENGINE = create_engine(f"sqlite:///{app_config['datastore']['filename']}")
Base.metadata.create_all(DB_ENGINE)
Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)


def publish_event_to_event_log(client, code, message, event_type):
    event_log_topic = client.topics[str.encode(app_config['events']['startup_topic'])]
    event_log_producer = event_log_topic.get_sync_producer()

    
    event_msg = {
        "type": event_type,
        "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": {
            "code": code,
            "message": message
        }
    }
    
    event_log_producer.produce(json.dumps(event_msg).encode('utf-8'))
    logger.info(f"Published message to Kafka topic '{event_log_topic}' with code {code}")


def get_stats():
    # get the latest row of stats from the database and return it as a dictionary
    session = DB_SESSION()
    stats = session.query(Statistics).order_by(Statistics.date_created.desc()).first()

    if stats is not None:
        results = stats.to_dict()
        logger.info("Query for statistics successful")
    else:
        results = {}
        logger.error("No statistics found")

    return results, 200


def populate_stats():
    """ Periodically update stats """
    # 1. Log an INFO message indicating periodic processing has started
    logger.info("Start Periodic Processing")
    logger.info("ASSIGNMENT2+1 Electric Boogaloo")
    
    # 2. Read in the current statistics from the SQLite database (filename defined in your configuration)
    try:
        session = DB_SESSION()
        stats = session.query(Statistics).order_by(Statistics.date_created.desc()).first()
        session.close()
    except Exception as e:
        logger.error(f"Exception during database access: {e}")
        return NoContent, 500

    # 2.1. If no stats yet exist, use default values for the stats
    if stats is None:
        logger.info("Stats table empty, adding default row now.")
        stats = Statistics(datetime.datetime.now(), 0, 0, 0, 0, 0)
    
    # 3. Get the current datetime
    current_datetime = datetime.datetime.now()
    try:
        # 4. Query the two GET endpoints from your Data Store Service (using requests.get) to get all new events from the last datetime you requested them (from your statistics) to the current datetime
        new_power_usage_events = requests.get(app_config['power-usage']['url'], 
                                            params={'start_timestamp': stats.date_created.strftime("%Y-%m-%dT%H:%M:%S"), 'end_timestamp': current_datetime.strftime("%Y-%m-%dT%H:%M:%S")})
        new_location_events = requests.get(app_config['location']['url'], 
                                        params={'start_timestamp': stats.date_created.strftime("%Y-%m-%dT%H:%M:%S"), 'end_timestamp': current_datetime.strftime("%Y-%m-%dT%H:%M:%S")})
    except Exception as e:
        logger.error(f"Unable to GET request from Storage: {e}")

    # 4.1. Log an INFO message with the number of events received
    logger.info(f"Received {len(new_power_usage_events.json())} power usage and {len(new_location_events.json())} location events")

    # 4.2. Log an ERROR message if you did not get a 200 response code
    if new_power_usage_events.status_code != 200 or new_location_events.status_code != 200:
        logger.error("Failed to get events from Data Store Service")
        return NoContent, 404
    
    messages_processed = len(new_power_usage_events.json()) + len(new_location_events.json())
    if messages_processed > app_config['message_threshold']:
        publish_event_to_event_log(client, "0004", f"Processed more than {app_config['message_threshold']} messages.", "large_processor_event")

    # 5. Based on the new events from the Data Store Service:
    try:
        # 5.1. Calculate your updated statistics
        if len(new_power_usage_events.json()) > 0:
            sum_of_soc_readings = 0

            for event in new_power_usage_events.json():
                if event['power_data']['power_W'] > stats.max_power_W:
                    stats.max_power_W = event['power_data']['power_W']

                if event['power_data']['temperature_C'] > stats.max_temperature_C:
                    stats.max_temperature_C = event['power_data']['temperature_C']

                sum_of_soc_readings += event['power_data']['state_of_charge_%']

                # 5.2. Log a DEBUG message for each event processed that includes the trace_id 
                logger.debug(f"event with trace_id {event['trace_id']} has been processed.")

            stats.average_state_of_charge = ((stats.average_state_of_charge * stats.total_power_usage_events) + 
                                            sum_of_soc_readings)/(stats.total_power_usage_events + len(new_power_usage_events.json()))
            
            stats.total_power_usage_events += len(new_power_usage_events.json())
            if len(new_location_events.json()) > 0:
                stats.total_location_events += len(new_location_events.json())
    except Exception as e:
        logger.error(f"Step 5: {e}")

    

    # 5.3. Write the updated statistics to the SQLite database file (filename defined in your configuration)
    try:
        session = DB_SESSION()

        updated_stats = Statistics(
            current_datetime,
            stats.total_power_usage_events,
            stats.max_power_W,
            stats.average_state_of_charge,
            stats.max_temperature_C,
            stats.total_location_events
        )

        session.add(updated_stats)
        session.commit()
        session.close()
    except Exception as e:
        logger.error(f"Exception during database access: {e}")
        return NoContent, 500
    
    # 5.4. Log a DEBUG message with your updated statistics values
    logger.debug(f"The updated statistics is as follows: \
                 Max Power (W)={stats.max_power_W}, \
                 Max Temperature (C)={stats.max_temperature_C}, \
                 Average State of Charge (%)={stats.average_state_of_charge}, \
                 Total Location Events Processed={stats.total_location_events}, \
                 Total Power Usage Events Processed={stats.total_power_usage_events}.")
    # 6. Log an INFO message indicating period processing has ended
    logger.info("The period processing has ended.")


def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats, 'interval', seconds=app_config['scheduler']['period_sec'])
    sched.start()


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml", base_path="/processing", strict_validation=True, validate_responses=True)

app.add_middleware(
    CORSMiddleware,
    position=MiddlewarePosition.BEFORE_EXCEPTION,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    retry_count = 0
    # Initialize KafkaClient with your Kafka server details
    while (retry_count < app_config['max_retries']):
        logger.info("Attempting to connect to Kafka. Attempt #: %s", retry_count + 1)
        try:
            client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
            break
        except Exception as e:
            logger.error("Failed to connect to Kafka on attempt #:%s, error: %s", retry_count + 1, e)
            time.sleep(app_config['sleep_time'])
            retry_count += 1
    else:
        logger.error("Exceeded maximum number of retries (%s) for Kafka connection", app_config['max_retries'])

    publish_event_to_event_log(client, "0003", "Processor successfully started.", "processor_startup")

    init_scheduler()
    app.run(host='0.0.0.0', port=8100)

