import yaml
import json
import csv
from loguru import logger
from gql import gql
from nested_lookup import nested_lookup as nl
from nested_lookup import get_all_keys
from flatten_dict import flatten

logger.add('demo_client.log', rotation="500 MB", retention="10 days", level='DEBUG')

rows_written_to_raw_log: int = 0
rows_written_to_csv: int = 0
pages_processed: int = 0
wrote_csv_header = False
columns: list = list()


def get_settings():
    """Reads the settings.yaml file and returns the variables and values
    :returns data: setting variables and values
    :rtype data: dict
    """
    with open('settings.yaml') as f:
        data: dict = yaml.load(f, Loader=yaml.FullLoader)
    return data


def read_query_file():
    settings = get_settings()
    file_name = settings['name_of_gql_query_file']
    with open(file_name, 'r') as f:
        return f.read()


def write_raw(data: dict):
    settings = get_settings()
    name_of_raw_output_file = settings['name_of_raw_output_file']
    if not name_of_raw_output_file:
        return
    with open(name_of_raw_output_file, 'a+') as f:
        f.write(json.dumps(data, indent=4))


def write_csv(data: dict):
    global rows_written_to_csv, wrote_csv_header, columns
    settings = get_settings()
    name_of_csv_file = settings['name_of_csv_file']
    if not name_of_csv_file:
        return
    flat: dict = flatten(data, reducer='dot')
    columns = get_all_keys(flat)
    try:
        with open(name_of_csv_file, 'a+') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            # logger.debug(f"WROTE HEADER: {wrote_csv_header}")
            if not wrote_csv_header:
                writer.writeheader()
                wrote_csv_header = True
            writer.writerow(flat)
            rows_written_to_csv += 1
    except Exception:
        raise



def get_info():
    info: str = ''
    settings = get_settings()
    raw_log_path: str = ''
    csv_path: str = ''
    try:
        raw_log_path = settings['name_of_raw_output_file']
    except KeyError:
        pass  # handle below
    info += f'\nTOTAL PAGES PROCESSED: {pages_processed}'
    if raw_log_path:
        info += f'\nTOTAL PAGES WRITTEN TO RAW LOG: {rows_written_to_raw_log}'

    return info


# def write_to_bq(data: dict):
#     settings = get_settings()
#     gcp_dataset_id: str = ''
#     gcp_project_id: str = ''
#     gcp_table_id: str = ''
#     try:
#         gcp_dataset_id = settings['gcp_dataset_id']
#         gcp_project_id = settings['gcp_project_id']
#         gcp_table_id = settings['gcp_table_id']
#     except KeyError:
#         pass  # check for the values below
#     if not gcp_dataset_id or not gcp_project_id or not gcp_table_id:
#         return
#     # build schema members
#     schema_members: list = list()
#     for column in columns:
#         tmp = (column, 'STRING')
#         schema_members.append(tmp)
#
#     bq = googleBigQueryTools.BQ(gcp_project_id=gcp_project_id,
#                                 gcp_dataset_id=gcp_dataset_id,
#                                 gcp_table_id=gcp_table_id,
#                                 schema_members=schema_members)
#     bq.create_dataset()
#     bq.create_table()
#     rows = list(data)
#     bq.push_rows(rows)


def run():
    global pages_processed, rows_written_to_raw_log
    settings = get_settings()
    pages_to_process = settings['pages_to_process']
    # make a client connection
    client = helpers.get_gql_client(settings=settings)

    # read file
    query = read_query_file()
    if not "pageInfo" or not "endCursor" or not "hasNextPage" in query:
        logger.error("Please include pageInfo in the query, it is required for paging.  See the README.md")
        return
    while True:
        query = read_query_file()
        if not "pageInfo" or not "endCursor" or not "hasNextPage" in query:
            logger.error("Please include pageInfo in the query, it is required for paging.  See the README.md")
            return
        response: dict = dict()
        try:
            response = client.execute(gql(query))
        except (ValueError, IndexError):
            raise
        pages_processed += 1
        if pages_processed >= pages_to_process:
            break
        cursor: str = ''
        try:
            cursor = nl('endCursor', response)[0]
        except (ValueError, IndexError):
            raise
        if response:
            nodes: list = nl('nodes', response)[0]
            for data in nodes:
                write_csv(data=data)
                write_raw(data=data)
        if not cursor:
            break





if __name__ == '__main__':
    run()
    logger.info(get_info())
    logger.info("Done")
