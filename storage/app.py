import connexion
from connexion import NoContent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from base import Base
from power_usage import PowerUsage
from location import Location
import datetime
import yaml
import logging
import logging.config
import json
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread
import time
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

logger.info(f"Connecting to DB. Hostname:{app_config['datastore']['hostname']}, Port:{app_config['datastore']['port']}")

# Create the database connection
DB_ENGINE = create_engine(f"mysql+pymysql://"
                          f"{app_config['datastore']['user']}:"
                          f"{app_config['datastore']['password']}@"
                          f"{app_config['datastore']['hostname']}:"
                          f"{app_config['datastore']['port']}/"
                          f"{app_config['datastore']['db']}",
                          pool_size=app_config['pool_size'],
                          pool_recycle=app_config['pool_recycle'],
                          pool_pre_ping=app_config['pool_pre_ping'])


Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)


def publish_startup_event(client):
    """Publish a startup message to the 'event_log' topic"""
    event_log_topic = client.topics[str.encode(app_config['events']['startup_topic'])]
    
    event_log_producer = event_log_topic.get_sync_producer()

    startup_msg = {
        "type": "storage_startup",
        "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": {
            "code": "0002",
            "message": "Storage is ready to receive messages on its RESTful API."
        }
    }
    
    event_log_producer.produce(json.dumps(startup_msg).encode('utf-8'))
    logger.info("Published startup message to Kafka topic 'event_log'")


def report_power_usage_reading(body):
    """ Receives a power usage reading """

    session = DB_SESSION()

    print(body)

    power_usage_instance = PowerUsage(body['device_id'],
                                      body['device_type'],
                                      body['timestamp'],
                                      body['power_data']['energy_out_Wh'],
                                      body['power_data']['power_W'],
                                      body['power_data']['state_of_charge_%'],
                                      body['power_data']['temperature_C'],
                                      body['trace_id'])
    
    print(power_usage_instance)

    session.add(power_usage_instance)

    logger.debug(f"Stored event power_usage request with a trace_id of {body['trace_id']}")

    session.commit()
    session.close()

    return NoContent, 201


def report_location_reading(body):
    """ Receives a location reading """

    session = DB_SESSION()

    location_instance = Location(body['device_id'],
                                 body['device_type'],
                                 body['timestamp'],
                                 body['location_data']['gps_latitude'],
                                 body['location_data']['gps_longitude'],
                                 body['trace_id'])

    session.add(location_instance)

    logger.debug(f"Stored event location request with a trace_id of {body['trace_id']}")

    session.commit()
    session.close()

    return NoContent, 201


def retrieve_power_usage_readings(start_timestamp, end_timestamp):
    session = DB_SESSION()
    logger.info("Retrieving power usage readings from %s to %s", start_timestamp, end_timestamp)

    start_timestamp_datetime = datetime.datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S")
    end_timestamp_datetime = datetime.datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S")

    readings = session.query(PowerUsage).filter(PowerUsage.date_created >= start_timestamp_datetime,
                                                PowerUsage.date_created < end_timestamp_datetime)
    
    results_list = []

    for reading in readings:
        results_list.append(reading.to_dict())

    session.close()

    logger.info("Query for power usage readings after %s returns %d results", start_timestamp, len(results_list))

    return results_list, 200


def retrieve_location_readings(start_timestamp, end_timestamp):
    try:
        session = DB_SESSION()
        logger.info("Retrieving location readings from %s to %s", start_timestamp, end_timestamp)

        start_timestamp_datetime = datetime.datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S")
        end_timestamp_datetime = datetime.datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S")

        readings = session.query(Location).filter(Location.date_created >= start_timestamp_datetime, 
                                                Location.date_created < end_timestamp_datetime)
        results_list = []

        for reading in readings:
            print(reading.to_dict())
            results_list.append(reading.to_dict())

        session.close()

        logger.info("Query for location readings after %s returns %d results", start_timestamp, len(results_list))

        return results_list, 200
    except Exception as e:
        print(e)


def process_messages():
    """ Process event messages """
    hostname = "%s:%d" % (app_config["events"]["hostname"], app_config["events"]["port"])

    retry_count = 0

    while (retry_count < app_config['max_retries']):
        logger.info("Attempting to connect to Kafka. Attempt #: %s", retry_count + 1)
        try:
            client = KafkaClient(hosts=hostname)
            publish_startup_event(client)
            topic = client.topics[str.encode(app_config["events"]["topic"])]
            logger.info("Successfully connected to Kafka on attempt #: %s", retry_count + 1)
            break
        except Exception as e:
            logger.error("Failed to connect to Kafka on attempt #:%s, error: %s", retry_count + 1, e)
            time.sleep(app_config['sleep_time'])
            retry_count += 1
    else:
        logger.error("Exceeded maximum number of retries (%s) for Kafka connection", app_config['max_retries'])
            

    # Create a consume on a consumer group, that only reads new messages
    # (uncommitted messages) when the service re-starts (i.e., it doesn't read all the old messages from the history in the message queue).
    consumer = topic.get_simple_consumer(consumer_group=b'event_group', reset_offset_on_start=False, auto_offset_reset=OffsetType.LATEST)

    # This is blocking - it will wait for a new message
    for msg in consumer:
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        logger.info("Message: %s" % msg)
        
        payload = msg["payload"]

        if msg["type"] == "power_usage": # Change this to your event type
            # Store the event1 (i.e., the payload) to the DB
            report_power_usage_reading(payload)
        elif msg["type"] == "location": # Change this to your event type
            # Store the event2 (i.e., the payload) to the DB
            report_location_reading(payload)
            
        # Commit the new message as being read
        consumer.commit_offsets()


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml", base_path="/storage", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    app.run(host='0.0.0.0', port=8090)
