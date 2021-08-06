from loguru import logger
from gql import gql
from utilities import helpers


class Paging(object):

    def __init__(self, response):
        self._response = response

    def get_pageInfo_elements(self):
        """ Gets the elements helpful for Paging
        
        Returns:
            endCursor(str) - pageInfo.endCursor value
            hasNext(bool) - pageInfo.hasNext value
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
        endCursor, hasNextPage = self.get_pageInfo_elements()
        logger.debug(f"Stop paging?  hasNextPage: {hasNextPage}, endCursor: {endCursor}")
        if not endCursor or not hasNextPage:
            return True
        elif hasNextPage and endCursor:
            return False


    def page_and_get_response(self, client, query, hasNextPage=True):
        if not self._response:
            try:
                self._response = client.execute(gql(query))
            except BaseException as e:
                logger.error(e)
                raise

        if self._should_stop_paging():
            hasNextPage = False
            return self._response, hasNextPage
        else:
            # there is more, so page
            endCursor, hasNextPage = self.get_pageInfo_elements()
            insert_text = f'after: "{endCursor}" '

            query = helpers.insert_into_query_header(query=query, insert_text=insert_text)
            try:
                self._response = client.execute(gql(query))
            except BaseException as e:
                logger.error(e)
                self._response = None
            return self._response, hasNextPage
