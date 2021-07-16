from google.cloud import bigquery
from keys import decode_keys


schema: list = list()
schema.append(bigquery.SchemaField(name='internal_timestamp', field_type='TIMESTAMP'))

for field in decode_keys:
    schema.append(bigquery.SchemaField(name=field, field_type='STRING'))


def get_bq_schema():
    return schema
