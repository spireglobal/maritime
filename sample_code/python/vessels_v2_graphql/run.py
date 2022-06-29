from operator import index
import yaml
import json
import datetime
from loguru import logger
from utilities import paging, helpers
from gql import gql
from nested_lookup import nested_lookup
import pandas as pd
import time


logger.add('demo_client.log', rotation="500 MB", retention="10 days", level='DEBUG')

pages_processed: int = 0
wrote_csv_header = False


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

def loadDataframe(data: dict):
    """Converts response from API call as dict to pandas dataframe ensuring all columns are listed
    :returns df: dataframe with rows from processed data
    :rtype df: pd.DataFrame
    """
     # get dict nodes
    nodes: list = nested_lookup('nodes', data)
    df = pd.DataFrame()
    for node_list in nodes:
        for node in node_list:

            flat: dict = helpers.flatten(node)            
            # BUG FOR FIELDS PARENTS WITH EMPTY VALUES (EX: Characteristics : Null). TEST WITH VARIOUS QUERIES
            csv_columns = helpers.get_all_keys(flat)
            df_node = pd.DataFrame(flat, columns=csv_columns, index=[0])
            if len(df) > 0:
                df = pd.concat([df, df_node], axis=0, ignore_index=True)
            else:
                df = df_node
    return df

def get_info():
    info: str = ''
    info += f'TOTAL PAGES PROCESSED: {pages_processed}'
    return info


def run():
    global pages_processed, rows_written_to_raw_log
    settings = get_settings()
    pages_to_process = settings['pages_to_process']
    name_of_csv_file = settings['name_of_csv_file']

    # make a client connection
    client = helpers.get_gql_client(settings=settings)

    # read file
    query = read_query_file()
    if not "pageInfo" or not "endCursor" or not "hasNextPage" in query:
        logger.error("Please include pageInfo in the query, it is required for paging.  See the README.md")
        return
    response: dict = dict()
    try:
        response = client.execute(gql(query))
    except BaseException as e:
        logger.error(e)
        raise
    if response:
        # initialize paging
        pg = paging.Paging(response=response)
        # schema_members = helpers.get_vessels_v2_members()

        # page, write, util complete
        logger.info("Paging started")
        hasNextPage: bool = False
        df_output = pd.DataFrame()
        df_output = pd.concat([df_output,loadDataframe(response)], axis=0, ignore_index=True)
        while True:
            response, hasNextPage = pg.page_and_get_response(client, query)
            if response:
                write_raw(response)
                pages_processed += 1
                logger.info(get_info())
                if name_of_csv_file:
                    df_output = pd.concat([df_output,loadDataframe(response)], axis=0, ignore_index=True)

                    if not hasNextPage:
                        if name_of_csv_file:
                            df_output.to_csv(name_of_csv_file, index= False)
                        break
                    elif pages_to_process and pages_processed >= pages_to_process:
                        if name_of_csv_file:
                            df_output.to_csv(name_of_csv_file, index= False)
                        break
            else:
                logger.info(
                    "Did not get data for csv, either because there are no more pages, or did not get a response")
                break

    else:
        logger.error('No response from the service')


if __name__ == '__main__':
    start = time.time()
    run()
    end = time.time()
    time_elapsed = datetime.timedelta(seconds=(end - start))
    logger.info(f"Time elapsed: {time_elapsed}")
    logger.info("Done")
