from tcp import TCP
import csv
from loguru import logger as log
from keys import decode_keys
import decoder
from utilities import clean_object_names
from bq import BQ
from utilities import Settings

if __name__ == '__main__':
    
    settings = Settings()
    log.add(settings.get_program_log(),  retention="10 days", rotation="500 MB")
    
    tcp = TCP(server=settings.get_server(), 
              port=settings.get_port(), 
              token=settings.get_token(), 
              max_messages=settings.get_max_messages(), 
              max_minutes=settings.get_max_minutes())
    data: list = tcp.get_data()
    
    if not data:
        raise Exception("NO DATA RETURNED")
    
    final: list = clean_object_names(decoder.parse_raw(data))
    

    raw_lines: list = tcp.get_raw_lines()
    
    csv_columns: list = list()

    if settings.get_csv_path():
        for key in decode_keys:
            csv_columns.append(key)
        try:
            with open(settings.get_csv_path(), 'a+') as f:
                writer = csv.DictWriter(f, fieldnames=csv_columns)
                writer.writeheader()
                item: dict
                for item in final:
                    writer.writerow(item)
        except BaseException as e:
            log.error(e)
            raise

        msg = f"""
        csv written: {settings.get_csv_path()}
        program log written: {settings.get_program_log()}
        raw tcp stream captured: {settings.get_raw_path()}
        """
        log.info(msg)

    if settings.get_raw_path():
        try:
            with open(settings.get_raw_path(), 'a+') as f:
                i: str
                for i in raw_lines:
                    f.write(i)
        except BaseException as e:
            log.error(e)
            raise


    if settings.get_gcp_project_id() and settings.get_gcp_dataset_id() and settings.get_gcp_table_id():
        # Write data to BQ
        BQ(gcp_project_id=settings.get_gcp_project_id(),
           gcp_dataset_id=settings.get_gcp_dataset_id(),
           gcp_table_id=settings.get_gcp_table_id(),
           data=final)
    else:
        log.info("ONE OR MORE BIG QUERY SETTINGS WERE NOT SET, SKIPPING WRITE TO BQ")

        
