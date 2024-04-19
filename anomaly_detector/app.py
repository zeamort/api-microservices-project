import connexion
from connexion import NoContent
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from base import Base
from anomaly_stats import AnomalyStats
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
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware

if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yaml"
    log_conf_file = "/config/log_conf.yaml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yaml"
    log_conf_file = "log_conf.yaml"

# Load the app_conf.yaml configuration 
with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())

# Load the log_conf.yaml configuration 
with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

# Create a logger for this file
logger = logging.getLogger('basicLogger')

logger.info("App Conf File: %s" % app_conf_file)
logger.info("Log Conf File: %s" % log_conf_file)

logger.info(f"Low SoC Threshold: {app_config['low_soc_threshold']}\n High Temp Threshold: {app_config['high_temp_threshold']}")

# Create the database connection
DB_ENGINE = create_engine(f"sqlite:///{app_config['datastore']['filename']}")
Base.metadata.create_all(DB_ENGINE)
Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)


def get_anomaly_stats():
    session = DB_SESSION()

    try:
        latest_row = session.query(AnomalyStats).order_by(AnomalyStats.date_created.desc()).first()
        if not latest_row:
            logger.error("No anomalies found")
            return {"message": "Anomalies do not exist"}, 404

        # Retrieve counts for each anomaly type
        stats = session.query(
            AnomalyStats.anomaly_type,
            func.count(AnomalyStats.anomaly_type).label('count')
        ).group_by(AnomalyStats.anomaly_type).all()

        # Construct a dictionary of anomaly types and their counts
        anomaly_counts = {anomaly_type: count for anomaly_type, count in stats}

        results = {
            "num_anomalies": anomaly_counts,  # Dictionary of counts for each anomaly type
            "most_recent_desc": latest_row.description,
            "most_recent_datetime": latest_row.date_created.strftime('%Y-%m-%d %H:%M:%S'),
        }

        logger.info("Query for anomaly statistics successful")
        return results, 200

    except Exception as e:
        logger.error(f"Error retrieving anomaly statistics: {e}")
        return {"message": "Invalid Anomaly Type"}, 400

    finally:
        session.close()


def report_anomaly(body, msg_type, anomaly_type, anomaly_message):
    """ Receives a power usage anomaly reading """

    session = DB_SESSION()

    anomaly_stats_instance = AnomalyStats(
        body['device_id'],
        body['trace_id'],
        msg_type,
        anomaly_type,
        anomaly_message
    )

    session.add(anomaly_stats_instance)

    logger.debug(f"Stored anomaly event power_usage request with a trace_id of {body['trace_id']}")

    session.commit()
    session.close()

    return NoContent, 201


def process_messages():
    # Create a consume on a consumer group, that only reads new messages
    # (uncommitted messages) when the service re-starts (i.e., it doesn't read all the old messages from the history in the message queue).
    consumer = topic.get_simple_consumer(consumer_group=b'event_group', reset_offset_on_start=False, auto_offset_reset=OffsetType.LATEST)

    # This is blocking - it will wait for a new message
    for msg in consumer:
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        # logger.info("Message: %s" % msg)

        payload = msg['payload']
        logger.info("Payload: %s" % payload)

        if msg["type"] == "power_usage":
            if payload['power_data']['state_of_charge_%'] < app_config['low_soc_threshold']:
                anomaly_type = "Low SoC"
                anomaly_message = f"SoC of {payload['power_data']['state_of_charge_%']}% is below the set safe threshold of {app_config['low_soc_threshold']}%"
                
                report_anomaly(payload, msg["type"], anomaly_type, anomaly_message)
            if payload['power_data']['temperature_C'] > app_config['high_temp_threshold']:
                anomaly_type = "High Temp"
                anomaly_message = f"Temperature of {payload['power_data']['temperature_C']}C is above the set safe threshold of {app_config['high_temp_threshold']}C"
                
                report_anomaly(payload, msg["type"], anomaly_type, anomaly_message)
            
        # Commit the new message as being read
        consumer.commit_offsets()


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml", base_path="/anomaly_detector", strict_validation=True, validate_responses=True)

app.add_middleware(
    CORSMiddleware,
    position=MiddlewarePosition.BEFORE_EXCEPTION,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    """ Process event messages """
    hostname = "%s:%d" % (app_config["events"]["hostname"], app_config["events"]["port"])

    retry_count = 0

    while (retry_count < app_config['max_retries']):
        logger.info("Attempting to connect to Kafka. Attempt #: %s", retry_count + 1)
        try:
            client = KafkaClient(hosts=hostname)
            topic = client.topics[str.encode(app_config["events"]["topic"])]
            logger.info("Successfully connected to Kafka on attempt #: %s", retry_count + 1)
            break
        except Exception as e:
            logger.error("Failed to connect to Kafka on attempt #:%s, error: %s", retry_count + 1, e)
            time.sleep(app_config['sleep_time'])
            retry_count += 1
    else:
        logger.error("Exceeded maximum number of retries (%s) for Kafka connection", app_config['max_retries'])

    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    app.run(host='0.0.0.0', port=8130)
