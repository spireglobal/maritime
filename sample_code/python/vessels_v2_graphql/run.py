from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
import yaml
from schema import schema
import json
import csv
from loguru import logger
from requests import exceptions

logger.add('demo_client.log', rotation="500 MB", retention="10 days", level='DEBUG')

rows_written_to_raw_log: int = 0
rows_written_to_csv: int = 0
pages_processed: int = 0


def get_settings():
    """Reads the settings.yaml file and returns the variables and values
    :returns data: setting variables and values
    :rtype data: dict
    """
    with open('settings.yaml') as f:
        data: dict = yaml.load(f, Loader=yaml.FullLoader)
    return data


def get_client():
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
        retries=2,
        timeout=5)
    try:
        client = Client(transport=transport, fetch_schema_from_transport=True)
    except exceptions.ConnectTimeout as e:
        logger.error(e)
        raise
    return client


def read_query_file():
    settings = get_settings()
    file_name = settings['name_of_gql_query_file']
    with open(file_name, 'r') as f:
        return f.read().replace('"', "'")


def page(response):
    global pages_processed, rows_written_to_raw_log, rows_written_to_csv
    settings = get_settings()
    pages_to_process = settings['pages_to_process']
    # we start at page 0, but setting would be 1 or more
    # page 1 is really page 0
    if pages_to_process != 0 and pages_to_process != 1:
        pages_to_process -= 1
    items_per_page = settings['items_per_page']
    metadata: dict = dict()
    try:
        metadata = response['vessels']['metadata']
    except KeyError:
        print("No metadata, can't page")
        raise
    cursor: str = metadata['cursor']
    hasMore: bool = metadata['hasMore']
    pages: int = 0
    client = get_client()
    query = read_query_file()
    after = metadata['after']


    # got one page
    if not after or pages_to_process == 1 or not hasMore:
        pages_processed = 1
        write_raw(response)
        write_csv(response)
        logger.info(get_info())
        return

    while hasMore:
        pages_processed += 1
        query = adjust_query(query=query, items_per_page=items_per_page, cursor=cursor, after=after)

        try:
            response: dict = client.execute(gql(query))
        except exceptions.ReadTimeout as e:
            logger.error(e)
            logger.info(get_info())
            raise

        write_raw(response)
        write_csv(response)
        hasMore = response['vessels']['metadata']['hasMore']
        after = response['vessels']['metadata']['after']

        # if limiting pages
        if pages >= pages_to_process > 0:
            logger.info("All pages processed")
            hasMore = False
            break
        pages += 1
        logger.info(f"""Processing page: {pages}""")
    logger.info(get_info())


def write_raw(data: dict):
    global rows_written_to_raw_log
    settings = get_settings()
    name_of_raw_output_file = settings['name_of_raw_output_file']
    if not name_of_raw_output_file:
        return
    with open(name_of_raw_output_file, 'a+') as f:
        f.write(json.dumps(data, indent=4))
    logger.debug(f"WROTE RESPONSE TO RAW LOG FILE: {name_of_raw_output_file}")
    rows_written_to_raw_log += 1


def write_csv(data: dict):
    global rows_written_to_csv
    vessels: list = data['vessels']['vessels']
    settings = get_settings()
    name_of_csv_file = settings['name_of_csv_file']
    if not name_of_csv_file:
        return
    csv_columns: list = list()
    for key in schema:
        csv_columns.append(key)
    try:
        with open(name_of_csv_file, 'a+') as f:
            writer = csv.DictWriter(f, fieldnames=csv_columns)
            writer.writeheader()
            item: dict
            for item in vessels:
                cleaned = clean(item)
                writer.writerow(cleaned)
                logger.debug(f"WROTE ROW TO CSV: {name_of_csv_file}")
                rows_written_to_csv += 1
    except Exception:
        raise


def clean(item: dict):
    cleaned: dict = dict()
    for key in schema:
        cleaned.setdefault(key, '')
    vessel = item['vessel']
    positionUpdate = item['positionUpdate']
    voyage = item['voyage']
    cleaned: dict = dict()
    for element, value in vessel.items():
        if element == 'dimensions':
            dimensions: dict = value
            cleaned['a'] = dimensions['a']
            cleaned['b'] = dimensions['b']
            cleaned['c'] = dimensions['c']
            cleaned['d'] = dimensions['d']
            cleaned['length'] = dimensions['length']
            cleaned['width'] = dimensions['width']
        elif element == 'timestamp':
            cleaned['vessel_timestamp'] = value
        else:
            cleaned[element] = value

    try:
        if positionUpdate:
            for element, value in positionUpdate.items():
                if element != 'timestamp':
                    cleaned[element] = value
                elif element == 'timestamp':
                    cleaned['position_timestamp'] = value
    except (KeyError, TypeError):
        return cleaned
    try:
        if voyage:
            for element, value in voyage.items():
                if element != 'timestamp':
                    cleaned[element] = value
                elif element == 'timestamp':
                    cleaned['voyage_timestamp'] = value
    except (KeyError, TypeError):
        return cleaned
    return cleaned


def adjust_query(query, items_per_page=100, cursor='', after=''):
    replace_this: str = 'vessels('
    with_this_replacement: str = ''
    if replace_this in query:
        with_this_replacement = f"""vessels( 
               _limit: {items_per_page}
               _after: "{after}"
               _cursor: "{cursor}"
           """
    q = query.replace(replace_this, with_this_replacement)
    return q


def get_info():
    info = f"""
            TOTAL PAGES WRITTEN TO RAW LOG: {rows_written_to_raw_log}
            TOTAL ROWS WRITTEN TO CSV: {rows_written_to_csv}
            TOTAL PAGES PROCESSED: {pages_processed}"""
    return info

def run():
    settings = get_settings()
    items_per_page = settings['items_per_page']
    # make a client connection
    client = get_client()
    # read file
    query = read_query_file()
    # get the items per page limit and insert it into the query

    # TODO what if customer query does not ask for metadata!

    if 'limit' not in query:
        query = adjust_query(query, items_per_page=items_per_page)
    # execute query and get results
    response = client.execute(gql(query))
    page(response)


if __name__ == '__main__':
    run()
