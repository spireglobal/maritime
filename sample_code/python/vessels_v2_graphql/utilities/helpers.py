import csv
import os
from datetime import datetime
import yaml
from gql import Client
from gql.transport.requests import RequestsHTTPTransport
from loguru import logger
from requests import exceptions
import json


def get_gql_client():
    """ Establishes a gql client 

    Returns:

        gql.client

    Raises:

        ConnectionTimeout

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
    """ Get a list of column names and the data types

    Returns:

        A list of column names and BigQuery data types

    These are added to support saving data that might be captured by a test
        'test_execute_start_time'
        'test_name'
    They can be null / empty string
    """

    return (
        ('row_insert_timestamp', "TIMESTAMP"),
        ('test_execute_start_time', "STRING"),
        ('test_name', "STRING"),
        ('nodes_updateTimestamp', "STRING"),
        ('id', "STRING"),
        ('staticData_updateTimestamp', "STRING"),
        ('staticData_timestamp', "STRING"),
        ('mmsi', "string"),
        ('imo', 'string'),
        ('name', 'string'),
        ('callsign', 'string'),
        ('shipType', 'string'),
        ('shipSubType', 'STRING'),
        ('aisClass', 'string'),
        ('flag', 'string'),
        ('length', 'string'),
        ('width', 'string'),
        ('a', 'string'),
        ('b', 'string'),
        ('c', 'string'),
        ('d', 'string'),
        ('lastPositionUpdate_updateTimestamp', "STRING"),
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
        ('currentVoyage_updateTimestamp', "STRING"),
        ('currentVoyage_timestamp', "STRING"),
        ('draught', 'string'),
        ('eta', 'string'),
        ('destination', 'string'),
        ('matchedPort_name', 'string'),
        ('matchedPort_unlocode', 'string'),
        ('matchedPort_lat', 'string'),
        ('matchedPort_long', 'string'),
        ('matchedPort_score', 'FLOAT')
    )


def transform_response_for_loading(response, schema, test_name='', test_execute_start_time=None):
    """Flattens complex response dictionary
    Args:

        response(dict) - response from GQL Query
        schema(list) - a list of keys and BQ datatypes, can be derived from get_vessels_v2_members
        test_name(str) - optional
        test_execute_start_time(datetime) - optional

    Returns:
        list of flattend dictionaries

    """
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
        flat["nodes_updateTimestamp"] = node["updateTimestamp"]

        # vessel in node
        vessel: dict = node['staticData']
        for k, v in vessel.items():
            if k == "updateTimestamp":
                flat["staticData_updateTimestamp"] = v
            elif k == 'timestamp':
                flat['staticData_timestamp'] = v
            elif k == 'dimensions':
                dimensions: dict = v
                for key, value in dimensions.items():
                    flat[k] = value
            else:
                if not k == 'dimensions':
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
                if k == "updateTimestamp":
                    flat["lastPositionUpdate_updateTimestamp"] = v
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
                if k == "updateTimestamp":
                    flat['currentVoyage_updateTimestamp'] = v
                elif k == 'timestamp':
                    flat['currentVoyage_timestamp'] = v
                elif k == 'matchedPort':
                    try:
                        flat['matchedPort_score'] = currentVoyage['matchedPort']['matchScore']
                    except (KeyError, TypeError):
                        logger.error(f"""
                                     matchedPort error

                                     {node}

                                     """)

                    port: dict = dict()
                    try:
                        port = currentVoyage['port']
                    except (KeyError, TypeError):
                        logger.error(f"""
                                     No port for matchedPort

                                     {node}

                                     """)
                    try:
                        centerPoint = port['centerPoint']
                        flat['matchedPort_name'] = centerPoint['mathedPort']['name']
                        flat['matchedPort_unlocode'] = centerPoint['matchedPort']['unlocode']
                        latitude = centerPoint['latitude']
                        longitude = centerPoint['longitude']
                        flat['matchedPort_lat'] = latitude
                        flat['matchedPort_long'] = longitude
                    except (KeyError, TypeError):
                        logger.error(f"""
                                     No centerPoint

                                     {node}

                                     """)
                else:
                    if not v:
                        v = ''
                    flat[k] = v
        try:
            # in case somehow these got into the dictionary
            del flat['dimensions']
            del flat['currentVoyage']
        except KeyError:
            pass
        flats.append(flat)
    return flats


def get_settings():
    """Reads the settings.yaml file and returns the variables and values

    Returns
        data(dict) - contains setting key, value pairs
    """
    with open('settings.yaml') as f:
        data: dict = yaml.load(f, Loader=yaml.FullLoader)
    return data


def format_datetime(dt: datetime):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def insert_into_query_header(query, insert_text=''):
    """Insert text into query header

    Args:
        query(str) - query string
        insert_text(str) - text to insert

    Returns
        new_query(str) - text with insert

    """
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
    """Get a list of files from directory

    Args:
        directory(str) - name of directory

    Returns:
        csvs(list) - list of files in directory
    """
    files = os.listdir(directory)
    csvs: list = [file for file in files if '.csv' in file]
    return csvs


def write_list_to_csv(data: list, csv_columns, directory):
    """ Write list of data to CSV

    Args:
        data(list) - list containing dictionaries to write
        csv_columns(list) - list of column names
        directory(str) - writes csv to this directory
    """

    fname: str = f'{datetime.utcnow()}.csv'
    write_directory(directory)
    full = directory + '/' + fname

    try:
        with open(full, 'a+') as f:
            writer = csv.DictWriter(f, fieldnames=csv_columns)
            writer.writeheader()
            writer.writerows(data)
    except FileNotFoundError as e:
        logger.error(e)
        raise


def write_directory(dirname):
    try:
        os.mkdir(dirname)
    except FileExistsError:
        pass


def write_to_file(data, file: str):
    """Writes to a file

    Args:
        data(Any) - data to write to text file
        file(str) - path and name of target files

    Raises:
        FileNotFoundError
    """
    try:
        with open(file, 'a+') as f:
            f.write(json.dumps(data, indent=4))
    except FileNotFoundError as e:
        logger.error(e)
        raise


def csv_to_dict(csv_file: str):
    """
    Takes a csv and returns a dict

    Args:
        csv_file(str) - file path and name for csv to read
    Returns:
        dict - dictionary representing csv
    """
    dict_from_csv: dict = None
    try:
        with open(csv_file, "r") as f:
            dict_reader = csv.DictReader(f)
            ordered_list_from_csv: list = list(dict_reader)[0]
            dict_from_csv = dict(ordered_list_from_csv)
    except FileNotFoundError as e:
        logger.error(e)
        raise
    return dict_from_csv

