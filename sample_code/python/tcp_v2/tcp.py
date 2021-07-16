import socket
import backoff
from datetime import datetime, timedelta
import time
from loguru import logger as log

class TCP(object):
    
    _lines_captured: list = list()
    reset_to_latest: bool = False
    reset_datetime: str = ''
    sock = None
    
    
    def __init__(
                    self,
                    server,
                    port,
                    token,
                    max_messages=0,
                    max_minutes=0,):
        self.server = server
        self.port = port
        self.token = token
        self.max_minutes = max_minutes
        self.max_messages = max_messages
        if not max_messages and not max_minutes:
            msg = f"""
            Either max_messages or max_minutes must be set
            max_messages (-ms): {max_messages}
            max_minutes (-mm): {max_minutes}
            """
            log.error(msg)
            raise ValueError(msg)
        if max_messages and max_minutes:
            msg = f"""
            Set only one of these, not both
            max_messages (-ms): {max_messages}
            max_minutes (-mm):  {max_minutes}                 
            """
            log.error(msg)
            raise ValueError(msg)
        
    def _setup_sock(self):
        """
        Initialize socket
        :return: None
        """
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(90)
            self.sock.connect((self.server, self.port))
        except socket.error as e:
            log.error(e)
            raise ConnectionError(e)
        finally:
            log.debug("SOCKET SET")
        
    @backoff.on_exception(
        backoff.expo,
        OSError,
        max_time=900,
        max_tries=20
    )
    def _connect(self):
        """Authenticate
        """
        self._setup_sock()
        if not self.reset_to_latest and not self.reset_datetime:
            login = 'A|T|' + self.token + '|' + '\n'
        elif self.reset_to_latest and not self.reset_datetime:
            login = 'A|T|' + self.token + '|resetToLatest' + '\n'
        else:
            login = 'A|T|' + self.token + f'|{self.reset_datetime}' + '\n'

        e = self.sock.sendall(login.encode('ASCII'))
        connected = not bool(e)
        if not connected:
            log.error(e)
            raise (f'CONNECTION ERROR\n{e}')
        else:
            log.debug(f"""
            CONNECTED
            token: {self.token}
            reset to latest: {self.reset_to_latest}
            reset to date: {self.reset_datetime}
            login: {login}
            """)

    def _read(self):
        """
        Gets stream data from socket
        :returns: raw data from socket
        :rtype: str
        """
        try:
            received = self.sock.recv(4096)
            if received:
                return received
        except socket.timeout as e:
            log.error(e)
            raise TimeoutError(e)

    def _get_lines(self):
        """Handles getting a full/complete line
        :yeilds: single lines as str or "NO" if no lines
        """
        temp_buffer = self._read()
        buffering = False
        if not temp_buffer:
            yield "NO"
        else:
            buffering = True
            temp_buffer = temp_buffer.decode()

        while buffering:
            if "\n" in temp_buffer:
                (line, temp_buffer) = temp_buffer.split("\n", 1)
                yield line + "\n"
            else:
                more = self._read()
                more = more.decode()
                buffering = bool(more)
                if not more:
                    break
                else:
                    temp_buffer += more
        if temp_buffer:
            yield temp_buffer
        else:
            yield "NO"
        
    def get_data(self):
        """Coordinates capturing and processing raw stream
        :returns: decoded data
        :rtype: list
        """
        result: list = list()
        
        # Make TCP connection
        self._connect()
        
        # Determine start time for later use 
        # in terminating capture of max_minutes
        start_time = 0
        end_time = 0
        if self.max_minutes:
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes= int(self.max_minutes))
            msg = f"""
            max_minutes: {self.max_minutes}
            start_time: {start_time}
            end_time: {end_time}
            """
            log.debug(msg)
        
        # Get raw lines of stream
        reply = self._get_lines()
        for line in reply:
            if 'Keep-alive' in line:
                continue
            # Try another connection if no lines were yeilded
            if line == "NO":
                log.debug("NO LINE, SLEEPING 5 SECONDS")
                time.sleep(5)
                self.sock.close()
                self._connect()
                continue
            else:
                self._lines_captured.append(line)
                if len(self._lines_captured) % 1000000 == 0:
                    log.debug(f"READ LINE TOTAL: {len(self._lines_captured)}")
            
            # Stop getting lines if max_messages is reached
            if self.max_messages:
                if len(self._lines_captured) >= int(self.max_messages):
                    log.info(f"MAXIMUM MESSAGES HAVE BEEN CAPTURED: {self.max_messages}")
                    return self._lines_captured
                
            # Stop getting lines if max_minutes is reached
            if self.max_minutes and start_time and end_time:
                now = datetime.now()
                elapsed_time = now - start_time
                msg = f"""
                max_minutes: {self.max_minutes}
                start_time: {start_time}
                end_time: {end_time}
                elapsed time: {elapsed_time}
                """
                log.trace(msg)
                if now >= end_time:
                    log.info(f"MAXIMUM MINUTES HAVE PASSED, STOP CAPTURE: {self.max_minutes} minutes")
                    return self._lines_captured
        return self._lines_captured

    def get_raw_lines(self):
        return self._lines_captured
    
    
