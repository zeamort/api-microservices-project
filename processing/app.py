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

# Load the app_conf.yaml configuration 
with open('app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())

# Load the log_conf.yml configuration 
with open('log_conf.yaml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

# Create a logger for this file
logger = logging.getLogger('basicLogger')

# Create the database connection
DB_ENGINE = create_engine(f"sqlite:///{app_config['datastore']['filename']}")
Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)


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
        stats = Statistics(datetime.datetime.now(), 0, 0, 0, 0, 0)
    
    # 3. Get the current datetime
    current_datetime = datetime.datetime.now()
    
    # 4. Query the two GET endpoints from your Data Store Service (using requests.get) to get all new events from the last datetime you requested them (from your statistics) to the current datetime
    new_power_usage_events = requests.get(app_config['power-usage']['url'], 
                                          params={'start_timestamp': stats.date_created.strftime("%Y-%m-%dT%H:%M:%S"), 'end_timestamp': current_datetime.strftime("%Y-%m-%dT%H:%M:%S")})
    new_location_events = requests.get(app_config['location']['url'], 
                                       params={'start_timestamp': stats.date_created.strftime("%Y-%m-%dT%H:%M:%S"), 'end_timestamp': current_datetime.strftime("%Y-%m-%dT%H:%M:%S")})

    # 4.1. Log an INFO message with the number of events received
    logger.info(f"Received {len(new_power_usage_events.json())} power usage and {len(new_location_events.json())} location events")

    # 4.2. Log an ERROR message if you did not get a 200 response code
    if new_power_usage_events.status_code != 200 or new_location_events.status_code != 200:
        logger.error("Failed to get events from Data Store Service")
        return NoContent, 404


    # 5. Based on the new events from the Data Store Service:
    
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
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    init_scheduler()
    app.run(port=8100)

