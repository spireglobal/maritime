from loguru import logger
from gql import gql
from utilities import helpers


class Paging(object):

    def __init__(self, response):
        self._response = response

    def get_paging_input_string(self, first=1000, after=''):
        return f"""
        first: {first}
        after: "{after}"
        """

    def _get_pageInfo_elements(self):
        """
        :returns: endCursor, hasNext
        :type endCursor: str
        :type hasNext: bool
        """
        response = self._response
        if not response:
            logger.error("Did not get response, can't get paging information")
            raise Exception
        pageInfo = response['vessels']['pageInfo']
        endCursor: str = pageInfo['endCursor']
        hasNextPage: bool = pageInfo['hasNextPage']
        return endCursor, hasNextPage

    def _should_stop_paging(self):
        # pageInfo.hasNextPage: false and pageInfo.endCursor: null
        endCursor, hasNextPage = self._get_pageInfo_elements()
        if not endCursor or not hasNextPage:
            return True
        return False

    def page_and_get_response(self, client, query, hasNextPage=True):
        if not self._response:
            try:
                self._response = client.execute(gql(query))
            except BaseException as e:
                logger.error(e)
                raise

        if self._should_stop_paging():
            return self._response
        else:
            # there is more, so page
            endCursor, hasNextPage = self._get_pageInfo_elements()
            insert_text = f'after: "{endCursor}" '

            query = helpers.insert_into_query_header(query=query, insert_text=insert_text)
            try:
                self._response = client.execute(gql(query))
            except BaseException as e:
                logger.error(e)
                self._response = None
            return self._response, hasNextPage