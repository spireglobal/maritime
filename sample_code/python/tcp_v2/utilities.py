from datetime import datetime
import yaml
from loguru import logger as log


class Settings(object):
    _settings: dict = dict()

    def __init__(self):
        self._read_yaml()

    def _read_yaml(self):
        """Reads the settings.yaml file and returns the variables and values
        :returns data: setting variables and values
        :rtype data: dict
        """
        with open('settings.yaml') as f:
            self._settings = yaml.load(f, Loader=yaml.FullLoader)
        log.debug("SETTINGS FILE READ")

    def get_server(self):
        server = ''
        try:
            server = self._settings['server']
        except KeyError:
            log.error("No server provided.  Please specify in settings.yaml")
            raise
        return server

    def get_port(self):
        port = ''
        try:
            port = self._settings['port']
        except KeyError:
            log.error("No port provided.  Please specify in settings.yaml")
            raise
        return port

    def get_token(self):
        token = ''
        try:
            token = self._settings['token']
        except KeyError:
            log.error("No token provided.  Please specify in settings.yaml")
            raise
        return token

    def get_gcp_dataset_id(self):
        dataset = None
        try:
            dataset = self._settings['gcp_dataset_id']
        except KeyError:
            log.info("No Google dataset id provided, skipping write to big query")
        return dataset

    def get_gcp_table_id(self):
        table = None
        try:
            table = self._settings['gcp_table_id']
        except KeyError:
            log.info("No Google table id provided, skipping write to big query")
        return table

    def get_gcp_project_id(self):
        project = None
        try:
            project = self._settings['gcp_project_id']
        except KeyError:
            log.info("No Google table id provided, skipping write to big query")
        return project

    def get_max_messages(self):
        maximum = None
        try:
            maximum = self._settings['max_messages']
        except KeyError:
            log.info("No maximum messages specified. This may be expected. Specify in settings.yaml")
        return maximum

    def get_max_minutes(self):
        minutes = None
        try:
            minutes = self._settings['max_minutes']
        except KeyError:
            log.info("No maximum minutes specified. This may be expected. Specify in settings.yaml")
        return minutes

    def get_csv_path(self):
        csv_path = None
        try:
            csv_path = self._settings['csv_path']
        except KeyError:
            log.info("No csv file specified. This may be expected. Specify in settings.yaml")
        return csv_path

    def get_raw_path(self):
        raw_path = None
        try:
            raw_path = self._settings['raw_path']
        except KeyError:
            log.info("No raw log specified. This may be expected. Specify in settings.yaml")
        return raw_path

    def get_program_log(self):
        log_path = None
        try:
            log_path = self._settings['program_log']
        except KeyError:
            log.info("No program log specified. This may be expected. Specify in settings.yaml")
        return log_path


def extract_epoch(s):
    epoch_time = ''
    clean_time = s.replace("\\", "")
    c0 = clean_time.replace("!AIVDM", "")
    c = c0.replace("b'", "")
    c1 = c.replace("c:", "")
    c2 = c1[:10]
    for character in c2:
        if character.isnumeric():
            epoch_time += str(character)
    return epoch_time


def handle_time(stamp):
    """
    Converts stamp to datetime
    """
    if type(stamp) == str:
        result = datetime.fromtimestamp(
            int(stamp)).strftime('%Y-%m-%d %H:%M:%S')
    else:
        result = stamp.strftime('%Y-%m-%d %H:%M:%S')

    return result


def clean_object_names(rows: list):
    result: list = list()
    remove: dict = {

        'shiptype': 'ShipType.',
        'epfd': 'EpfdType.',
        'maneuver': 'ManeuverIndicator.',
        'status': 'NavigationStatus.',
    }
    for row in rows:
        for key, replace_this in remove.items():
            clean_me = str(row[key])
            row[key] = clean_me.replace(replace_this, '')
        result.append(row)
    return result
