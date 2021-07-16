from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
import yaml
from schema import schema
import json
import csv


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
        retries=3,
        timeout=10)
    client = Client(transport=transport, fetch_schema_from_transport=True)
    return client


def read_query_file():
    settings = get_settings()
    file_name = settings['name_of_gql_query_file']
    with open(file_name, 'r') as f:
        return f.read().replace('"', "'")


def page(response):
    settings = get_settings()
    pages_to_process = settings['pages_to_process']
    items_per_page = settings['items_per_page']
    metadata: dict = dict()
    try:
        metadata = response['vessels']['metadata']
    except KeyError:
        print("No metadata, can't page")
        raise
    cursor: str = metadata['cursor']
    hasMore: bool = True
    pages: int = 0
    client = get_client()
    query = read_query_file()

    # TODO replace is NOT working

    replace_this = """
    vessels{
                metadata{
                    cursor
                    correlationId
                    after
                    hasMore
                } 
    """
    while hasMore:
        if pages == 0:
            after = f"'{items_per_page - 1}'"
        else:
            after = metadata['after']
        q = query.replace(replace_this, f"vessels(_after: {after} _cursor: {cursor} _limit: {items_per_page})")
        response: dict = client.execute(gql(q))
        write_raw(response)
        write_csv(response)
        if pages_to_process:
            if pages >= pages_to_process:
                print("All pages processed")
                break
            else:
                pages += 1
                print(f"""Processing page: {pages}""")
    print("Done")


def write_raw(data: dict):
    settings = get_settings()
    name_of_raw_output_file = settings['name_of_raw_output_file']
    if not name_of_raw_output_file:
        return
    with open(name_of_raw_output_file, 'a+') as f:
        f.write(json.dumps(data, indent=4))


def write_csv(data: dict):
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


def run():
    # make a client connection
    client = get_client()
    # read file
    query = read_query_file()
    # execute query and get results
    response = client.execute(gql(query))
    page(response)


if __name__ == '__main__':
    run()
