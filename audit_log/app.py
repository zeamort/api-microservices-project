# import connexion
# from connexion import NoContent
# import yaml
# import logging
# import logging.config
# import json
# from pykafka import KafkaClient
# from pykafka.common import OffsetType
# from threading import Thread

# # Load the app_conf.yml configuration 
# with open('app_conf.yml', 'r') as f:
#     app_config = yaml.safe_load(f.read())

# # Load the log_conf.yml configuration 
# with open('log_conf.yml', 'r') as f:
#     log_config = yaml.safe_load(f.read())
#     logging.config.dictConfig(log_config)

# # Create a logger for this file
# logger = logging.getLogger('basicLogger')


# def get_power_usage_reading(index):
#     """ Get Power Usage Reading in History """
#     hostname = "%s:%d" % (app_config["events"]["hostname"], app_config["events"]["port"])
#     client = KafkaClient(hosts=hostname)
#     topic = client.topics[str.encode(app_config["events"]["topic"])]
#     consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=100)

#     logger.info("Retrieving Power Usage at index %d", index)
#     try:
#         current_index = 0
#         for message in consumer:
#             if message is not None and message.value is not None:
#                 msg_str = message.value.decode('utf-8')
#                 msg = json.loads(msg_str)

#                 # Uncomment the following lines if you want to process specific types of messages
#                 if msg["type"] != "power_usage":
#                     continue

#                 if current_index == index:
#                     logger.info("Found Power Usage at index %d", index)
#                     return msg, 200
#                 current_index += 1

#     except Exception as e:
#         logger.error("Error retrieving message: %s", str(e))

#     logger.error("Could not find Power Usage at index %d", index)
#     return {"message": "Not Found"}, 404



# def get_location_reading(index):
#     """ Get Location Reading in History """
#     hostname = "%s:%d" % (app_config["events"]["hostname"], app_config["events"]["port"])
#     client = KafkaClient(hosts=hostname)
#     topic = client.topics[str.encode(app_config["events"]["topic"])]

#     # Here we reset the offset on start so that we retrieve
#     # messages at the beginning of the message queue.
#     # To prevent the for loop from blocking, we set the timeout to
#     # 100ms. There is a risk that this loop never stops if the
#     # index is large and messages are constantly being received!
#     consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=100)

#     logger.info("Retrieving Location at index %d" % index)
#     try:
#         current_index = 0
#         for msg in consumer:
#             msg_str = msg.value.decode('utf-8')
#             msg = json.loads(msg_str)
#             print(f"this is the message: {msg}")
#             # Find the event at the index you want and
#             if current_index == index:
#                 logger.info("Found Location at index %d" % index)
#                 # return code 200
#                 # i.e., return event, 200
#                 return msg, 200
#             current_index += 1
#     except:
#         logger.error("No more messages found")

#     logger.error("Could not find Location at index %d" % index)
#     return { "message": "Not Found"}, 404


# def main():
#     app = connexion.FlaskApp(__name__, specification_dir='')
#     app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
#     app.run(port=8110)

# if __name__ == "__main__":
#     main()


import connexion
from connexion import NoContent
import yaml
import logging
import logging.config
import json
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread

# Load the application configuration
with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

# Load the logging configuration
with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

# Create a logger for this file
logger = logging.getLogger('basicLogger')

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
    app.run(port=8110)

if __name__ == "__main__":
    main()
