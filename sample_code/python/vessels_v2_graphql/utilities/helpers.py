from loguru import logger
import yaml
from nested_lookup import nested_lookup as nl
from datetime import datetime
from gql import Client
from gql.transport.requests import RequestsHTTPTransport
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
        ('node_ingestionTimestamp', "STRING"),
        ('vessel_ingestionTimestamp', "STRING"),
        ('vessel_timestamp', "STRING"),
        ('mmsi', "string"),
        ('imo', 'string'),
        ('name', 'string'),
        ('callsign', 'string'),
        ('shipType', 'string'),
        ('class', 'string'),
        ('flag', 'string'),
        ('length', 'string'),
        ('width', 'string'),
        ('a', 'string'),
        ('b', 'string'),
        ('c', 'string'),
        ('d', 'string'),
        ('position_ingestionTimestamp', "STRING"),
        ('position_timestamp', "STRING"),
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
        ('voyage_ingestionTimestamp', "STRING"),
        ('voyage_timestamp', "STRING"),
        ('draught', 'string'),
        ('eta', 'string'),
        ('destination', 'string'),
        # ('matched_port_name', 'string'),
        # ('matched_port_unlocode', 'string'),
        # ('matched_port_lat', 'string'),
        # ('matched_port_long', 'string'),
    )



def transform_response_for_loading(response, schema, test_name='', test_execute_start_time=None):

    v2_schema = [i[0] for i in schema]
    if not test_execute_start_time:
        test_execute_start_time = datetime.utcnow()

    nodes: list = response['vessels']['nodes']
    positionUpdates: list = nl('positionUpdate', response)
    voyages: list = nl('voyage', response)
    # flatten the dictionaries and add to flats list
    flats: list = list()
    node: dict
    for node in nodes:
        flat: dict = dict()
        for key in v2_schema:
            flat.setdefault(key, '')
        flat['row_insert_timestamp'] = "AUTO"
        flat['test_execute_start_time'] = test_execute_start_time
        flat['test_name'] = test_name
        flat["node_ingestionTimestamp"] = node["ingestionTimestamp"]

        # vessel in node
        vessel: dict = node['vessel']
        for k, v in vessel.items():
            if k == "ingestionTimestamp":
                flat["vessel_ingestionTimestamp"] = v
            elif k == 'timestamp':
                flat['vessel_timestamp'] = v
            elif k == 'dimensions':
                dimensions: dict = v
                for key, value in dimensions.items():
                    flat[k] = value
            else:
                if not k == 'dimensions':
                    flat[k] = v

        # positionUpdate in node
        positionUpdate: dict = dict()
        try:
            positionUpdate: dict = node['positionUpdate']
        except BaseException as e:
            logger.error(e)
            logger.error("Could be there is no positionUpdate")

        if positionUpdate:
            for k, v in positionUpdate.items():
                if k == "ingestionTimestamp":
                    flat["position_ingestionTimestamp"] = v
                elif k == 'timestamp':
                    flat['position_timestamp'] = v
                else:
                    flat[k] = v

        # voyage in node
        voyage: dict = dict()
        try:
            voyage = node['voyage']
        except BaseException as e:
            logger.error(e)
            logger.error("Could be there is no voyage")
        if voyage:
            for k, v in voyage.items():
                if k == "ingestionTimestamp":
                    flat['voyage_ingestionTimestamp'] = v
                elif k == 'timestamp':
                    flat['voyage_timestamp'] = v
                else:
                    flat[k] = v
        try:
            del flat['dimensions']
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


