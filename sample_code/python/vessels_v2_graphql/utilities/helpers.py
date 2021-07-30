import csv
import os
from datetime import datetime

import yaml
from gql import Client
from gql.transport.requests import RequestsHTTPTransport
from loguru import logger
from requests import exceptions


def get_gql_client():
    """
    :return: gql transport client
    :rtype: gql.Client
    """
    settings = get_settings()
    endpoint = settings['endpoint']
    token = settings['token']

    headers = dict()
    headers['Authorization'] = f'Bearer {token}'
    transport = RequestsHTTPTransport(
        url=endpoint,
        headers=headers,
        verify=True,
        retries=3,
        timeout=30)
    try:
        client = Client(transport=transport, fetch_schema_from_transport=True)
    except exceptions.ConnectTimeout as e:
        logger.error(e)
        raise
    return client


def get_vessels_v2_members():
    """
    These are added to support saving data that might be captured by a test
           'test_execute_start_time',
            'test_name',
    They can be null / empty string
    """

    return (
        ('row_insert_timestamp', "TIMESTAMP"),
        ('test_execute_start_time', "STRING"),
        ('test_name', "STRING"),
        ('nodes_ingestionTimestamp', "STRING"),
        ('staticInfo_ingestionTimestamp', "STRING"),
        ('staticInfo_timestamp', "STRING"),
        ('mmsi', "string"),
        ('imo', 'string'),
        ('name', 'string'),
        ('callsign', 'string'),
        ('shipType', 'string'),
        ('class', 'string'),
        ('flag', 'string'),
        ('dimensions_length', 'string'),
        ('dimensions_width', 'string'),
        ('antennaDistances_a', 'string'),
        ('antennaDistances_b', 'string'),
        ('antennaDistances_c', 'string'),
        ('antennaDistances_d', 'string'),
        ('lastPositionUpdate_ingestionTimestamp', "STRING"),
        ('lastPositionUpdate_timestamp', "STRING"),
        ('latitude', 'string'),
        ('longitude', 'string'),
        ('heading', 'string'),
        ('speed', 'string'),
        ('rot', 'string'),
        ('accuracy', 'string'),
        ('maneuver', 'string'),
        ('course', 'string'),
        ('navigationalStatus', 'string'),
        ('collectionType', 'string'),
        ('currentVoyage_ingestionTimestamp', "STRING"),
        ('currentVoyage_currentVoyage_timestamp', "STRING"),
        ('draught', 'string'),
        ('reportedETA', 'string'),
        ('reportedDestination', 'string'),
        # ('matchedPort_name', 'string'),
        # ('matchedPort_unlocode', 'string'),
        # ('matchedPort_lat', 'string'),
        # ('matchedPort_long', 'string'),
    )


def transform_response_for_loading(response, schema, test_name='', test_execute_start_time=None):

    if not test_execute_start_time:
        test_execute_start_time = datetime.utcnow()

    nodes: list = response['vessels']['nodes']
    # flatten the dictionaries and add to flats list
    flats: list = list()
    node: dict
    for node in nodes:
        flat: dict = dict()
        v2_schema = [i[0] for i in schema]
        for key in v2_schema:
            flat.setdefault(key, '')
        flat['row_insert_timestamp'] = "AUTO"
        flat['test_execute_start_time'] = test_execute_start_time
        flat['test_name'] = test_name
        flat["node_ingestionTimestamp"] = node["ingestionTimestamp"]

        # vessel in node
        vessel: dict = node['staticInfo']
        for k, v in vessel.items():
            if k == "ingestionTimestamp":
                flat["staticInfo_ingestionTimestamp"] = v
            elif k == 'timestamp':
                flat['staticInfo_timestamp'] = v
            elif k == 'dimensions':
                dimensions: dict = v
                for key, value in dimensions.items():
                    flat[k] = value
            elif k == 'antennaDistances':
                antennaDistances: dict = v
                for key, value in antennaDistances.items():
                    flat[k] = value

            else:
                if not k == 'dimensions' or not k == 'antennaDistances':
                    if not v:
                        v = ''
                    flat[k] = v

        # lastPositionUpdate in node
        lastPositionUpdate: dict = dict()
        try:
            lastPositionUpdate: dict = node['lastPositionUpdate']
        except BaseException as e:
            logger.error(e)
            logger.error("Could be there is no lastPositionUpdate")

        if lastPositionUpdate:
            for k, v in lastPositionUpdate.items():
                if k == "ingestionTimestamp":
                    flat["lastPositionUpdate_ingestionTimestamp"] = v
                elif k == 'timestamp':
                    flat['lastPositionUpdate_timestamp'] = v
                else:
                    if not v:
                        v = ''
                    flat[k] = v

        # currentVoyage in node
        currentVoyage: dict = dict()
        try:
            currentVoyage = node['currentVoyage']
        except BaseException as e:
            logger.error(e)
            logger.error("Could be there is no currentVoyage")
        if currentVoyage:
            for k, v in currentVoyage.items():
                if k == "ingestionTimestamp":
                    flat['currentVoyage_ingestionTimestamp'] = v
                elif k == 'timestamp':
                    flat['currentVoyage_timestamp'] = v
                else:
                    if not v:
                        v = ''
                    flat[k] = v
        try:
            # in case somehow these got into the dictionary
            del flat['dimensions']
            del flat['antennaDistances']
            del flat['lastPositionUpdate']
            del flat['currentVoyage']
        except KeyError:
            pass
        flats.append(flat)
    return flats


def get_settings():
    """Reads the settings.yaml file and returns the variables and values
    :returns data: setting variables and values
    :rtype data: dict
    """
    with open('settings.yaml') as f:
        data: dict = yaml.load(f, Loader=yaml.FullLoader)
    return data


def format_datetime(dt: datetime):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def insert_into_query_header(query, insert_text=''):
    if ')' in query:
        loc = query.find(')')
        # remove the existing )
        tmp: str = query.replace(')', '')
        # add paging elements where the ) once was .. + 1 for some spacing in case
        beginning: str = query[:loc]
        end: str = tmp[loc:]
        new_query = beginning + ' ' + insert_text + ' ) ' + end
    else:
        return query
    return new_query


def get_csv_list_from_dir(directory):
    files = os.listdir(directory)
    csvs: list = [file for file in files if '.csv' in file]
    return csvs


def write_data_to_csv(data: dict, csv_columns, directory):
    fname: str = f'{datetime.utcnow()}.csv'
    write_directory(directory)
    full = directory + '/' + fname

    try:
        with open(full, 'a+') as f:
            writer = csv.DictWriter(f, fieldnames=csv_columns)
            writer.writeheader()
            writer.writerow(data)
    except FileNotFoundError as e:
        logger.error(e)
        raise


def write_directory(dirname):
    try:
        os.mkdir(dirname)
    except FileExistsError:
        pass
