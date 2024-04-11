import connexion
from connexion import NoContent
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from base import Base
from stats import Statistics
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

# Create the database connection
DB_ENGINE = create_engine(f"sqlite:///{app_config['datastore']['filename']}")
Base.metadata.create_all(DB_ENGINE)
Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)


def event_stats():
    session = DB_SESSION()
    stats = session.query(
        Statistics.code, 
        func.count(Statistics.code).label('count')
    ).group_by(Statistics.code).all()

    if stats is not None:
        results = {code: count for code, count in stats}
        logger.info("Query for statistics successful")
    else:
        results = {}
        logger.error("No statistics found")

    return results, 200


def store_event_message(payload):
    session = DB_SESSION()

    event_log_instance = Statistics(payload['message'], payload['code'], datetime.datetime.now())

    session.add(event_log_instance)

    session.commit()
    session.close()

    return NoContent, 201


def process_messages():
    # Create a consume on a consumer group, that only reads new messages
    consumer = topic.get_simple_consumer(consumer_group=b'event_group', 
                                         reset_offset_on_start=False, 
                                         auto_offset_reset=OffsetType.LATEST)

    # This is blocking - it will wait for a new message
    for msg in consumer:
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        logger.info("Message: %s" % msg)
        
        payload = msg["payload"]

        store_event_message(payload)
            
        # Commit the new message as being read
        consumer.commit_offsets()


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml", base_path="/event_logger", strict_validation=True, validate_responses=True)

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

    while (retry_count < app_config['max_retries']):
        logger.info("Attempting to connect to Kafka. Attempt #: %s", retry_count + 1)
        try:
            client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
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

    app.run(host='0.0.0.0', port=8120)
