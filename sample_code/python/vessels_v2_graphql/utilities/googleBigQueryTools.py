from google.cloud import bigquery
from google.api_core import exceptions as gcx
from loguru import logger
import asyncio


class BQ(object):

    def __init__(self,
                 gcp_project_id,
                 gcp_dataset_id,
                 gcp_table_id,
                 schema_members):
        self._gcp_project_id = gcp_project_id
        self._gcp_dataset_id = gcp_dataset_id
        self._gcp_table_id = gcp_table_id
        self._schema_members = schema_members

    def _get_client(self):
        bigquery.DEFAULT_RETRY.with_deadline(10)
        return bigquery.Client(project=self._gcp_project_id)

    def _get_dataset_reference(self):
        return bigquery.dataset.DatasetReference(project=self._gcp_project_id,
                                                 dataset_id=self._gcp_dataset_id)

    def _get_table_reference(self):
        return bigquery.table.TableReference(dataset_ref=self._get_dataset_reference(),
                                             table_id=self._gcp_table_id)

    def get_schema(self):
        types = self._get_schema_field_types()
        members = self._schema_members
        schema: list = list()
        keys: list = list()
        for pair in members:
            key = pair[0]
            keys.append(key)
            data_type = pair[1].upper()
            if data_type not in types:
                logger.error(f"""
                Malformed schema_defs
                Type input: {data_type}
                Valid types: {types}
                """)
            schema.append(bigquery.SchemaField(name=key, field_type=data_type))
        return schema, keys

    def create_dataset(self):
        # Get dataset object
        dataset_reference = self._get_dataset_reference()
        dataset = bigquery.Dataset(dataset_reference)
        # Get client
        client = self._get_client()

        try:
            client.create_dataset(dataset)
        except (gcx.AlreadyExists, gcx.Conflict):
            return
        logger.debug(f'Dataset created: {dataset_reference}')
        try:
            client.get_dataset(dataset_ref=dataset_reference)
        except gcx.NotFound as e:
            msg = f"""
            Can not verify existing dataset
            {e}
            """
            logger.error(msg)
            raise gcx.NotFound(msg)

    def create_table(self):
        """Creates a table for test results if one does not exist
        """

        table = self._get_existing_table()
        table_reference = self._get_table_reference()
        client = self._get_client()
        schema, fields = self.get_schema()
        if not table:
            try:
                table = bigquery.Table(table_reference, schema)
                table.time_partitioning = bigquery.TimePartitioning(type_=bigquery.TimePartitioningType.DAY,
                                                                    field='row_insert_timestamp',
                                                                    expiration_ms=7776000000)
                client.create_table(table)
                logger.debug(f"Table created: {table_reference} ")
            except (gcx.AlreadyExists, gcx.Conflict):
                pass
        else:
            missing_fields = [f for f in fields if f not in str(table.schema)]
            print()
            if missing_fields:
                try:
                    client.update_table(table=table, fields=missing_fields)
                except BaseException as e:
                    logger.error(e)
                    raise
                logger.debug(f"Table updated with new fields: {table_reference} ")


    def _get_schema_field_types(self):
        return ("STRING",
                "BYTES",
                "INTEGER",
                "FLOAT",
                "BOOLEAN",
                "TIMESTAMP",
                "DATE",
                "TIME",
                "DATETIME",
                "GEOGRAPHY",
                "NUMERIC")

    def _get_existing_table(self):
        table_reference = self._get_table_reference()
        schema, keys = self.get_schema()
        client = self._get_client()
        table = False
        try:
            table = bigquery.Table(table_reference, schema)
            client.get_table(table)
        except gcx.NotFound:
            return False
        except (ValueError, gcx.BadRequest):
            return False
        return table

    def _insert_rows(self, rows):
        """Insert rows into the bq table"""
        client = self._get_client()
        table_reference = self._get_table_reference()
        table = client.get_table(table_reference)
        try:
            if not rows:
                return
            for row in rows:
                errors = client.insert_rows(table_reference, [row], table.schema)
                if errors:
                    logger.error(f"""BQ ERROR: 
                    {errors}""")
            del rows
        except gcx.BadRequest as b:
            logger.error(b)
            raise

        except OverflowError as e:
            logger.error(f"""
            Ignoring this OverflowError, just skipping this row
            {e}""")
            del rows
        except ValueError as e:
            logger.error(e)
            del rows

    async def insert_row_task(self, rows):
        self._insert_rows(rows)