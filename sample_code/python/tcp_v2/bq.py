from google.cloud import bigquery
from google.api_core import exceptions as gcx
from bq_schema import schema
from loguru import logger as log


class BQ(object):
    client = None

    def __init__(self,
                 gcp_project_id,
                 gcp_table_id,
                 gcp_dataset_id,
                 data=None):
        self.gcp_dataset_id = gcp_dataset_id
        self._gcp_project_id = gcp_project_id
        self._gcp_table_id = gcp_table_id
        self._data = data
        self._insert_rows()

    def _create_dataset(self, client, dataset_reference):

        """Create a BQ dataset if one does not exist
        :param client: BigQuery client
        :type client: google.cloud.bigquery.Client
        :param dataset_reference: the dataset name/id
        :type dataset_reference: google.cloud.bigquery.dataset.DatasetReference
        """
        dataset = bigquery.Dataset(dataset_reference)
        try:
            client.create_dataset(dataset)
        except (gcx.AlreadyExists, gcx.Conflict):
            log.debug("Dataset already exists, this may be an expected condition")
            return
        log.debug(f'Dataset created')
        try:
            client.get_dataset(dataset_ref=dataset_reference)
        except gcx.NotFound as e:
            msg = f"""
            Can not verify existing dataset
            {e}
            """
            log.error(msg)
            raise gcx.NotFound(msg)

    def _create_table(self, client, table_reference):

        """Creates a table for test results if one does not exist

        :param client: BigQuery client
        :type client: google.cloud.bigquery.Client
        :param table_reference: reference to bq table
        :type table_reference: google.cloud.bigquery.table.TableReference
        """

        table = bigquery.Table(table_reference, schema)
        table.time_partitioning = bigquery.TimePartitioning(type_=bigquery.TimePartitioningType.DAY,
                                                            field='internal_timestamp',
                                                            expiration_ms=7776000000)
        try:
            client.create_table(table)
        except (gcx.AlreadyExists, gcx.Conflict):
            log.info("Table already exists, this may be an expected condition")
            return
        log.info(f'Table created')
        try:
            client.get_table(table)
        except gcx.NotFound:
            log.error(f'ERROR: Can not verify existing table')
            raise Exception

    def _setup_bq_objects(self):

        """Helper sets up bigquery objects
        :returns: big query client, dataset_reference, table_reference
        """
        client = bigquery.Client(project=self._gcp_project_id)
        dataset_reference = bigquery.dataset.DatasetReference(project=self._gcp_project_id,
                                                              dataset_id=self.gcp_dataset_id)
        table_reference = bigquery.table.TableReference(dataset_ref=dataset_reference,
                                                        table_id=self._gcp_table_id)
        return client, dataset_reference, table_reference

    def _insert_rows(self):
        """Insert rows into the bq table 
        """
        client, dataset_reference, table_reference = self._setup_bq_objects()
        self._create_dataset(client, dataset_reference)
        self._create_table(client, table_reference)

        table = client.get_table(table_reference)
        rows: list = list()
        # for item in self._data:
        #     row = [f'{v}' for v in item.values()]
        #     rows.append(row)

        rows = self._data
        log.debug("ATTEMPTING TO WRITE BQ ROWS TO TABLE")
        try:
            count = 0
            for row in rows:
                count += 1
                errors = client.insert_rows(table_reference, [row], selected_fields=table.schema)
                if errors:
                    log.error(errors)
                else:
                    if count % 100000 == 0:
                        log.debug(f"{count} BQ ROWS INSERTED")

        except gcx.BadRequest as b:
            log.error(b)
        except OverflowError as e:
            log.error(f"""
            Ignoring this error, just skipping this row
            {e}""")

        log.debug("BQ WRITE ATTEMPT COMPLETE")
