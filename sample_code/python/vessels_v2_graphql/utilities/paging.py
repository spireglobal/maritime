from loguru import logger
from gql import gql
from utilities import helpers


class Paging(object):

    def __init__(self, response=None):
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
        if not endCursor:
            return True
        elif endCursor and hasNextPage:
            return False
        else:
            return False

    def get_response(self):
        return self._response

    def page_and_get_response(self, client, query, hasNextPage=True):
        """
        Args:
            client: gql client
            query(str): query string
            hasNextPage(bool): optional - paging element, is there a next page

        Returns:
            response(dict): service response to query
            hasNextPage(bool): paging element, is there a next page
        """
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
                logger.warning(e)
                self._response = False

            return self._response, hasNextPage

    def start_paging(self, client, query_text):
        page_count: int = 0
        end_time = None
        responses: list = list()  # to help with error reporting of last response
        while True:
            response: dict = dict()
            hasNextPage: bool = False
            try:
                response, hasNextPage = self.page_and_get_response(client, query_text)
                responses.append(response)
            except BaseException as e:
                logger.error(e)
                self._detailed_error(responses, page_count, hasNextPage)
                raise

            if not response and hasNextPage:
                self._detailed_error(responses, page_count, hasNextPage)
                assert False
            elif not hasNextPage and not response:
                logger.info("DONE PAGING, the 'error' below is just information")
                self._detailed_error(responses, page_count, hasNextPage)
            elif response:
                page_count += 1
                logger.info(f"Page: {page_count}")
                yield response, page_count

    def _detailed_error(self, responses, page, hasNextPage):
        if len(responses) > 4:
            responses.pop()  # control amount of RAM consumed
        previous = responses[len(responses) - 1]
        pretty_previous = helpers.pretty_string_dict(previous, with_empties=False)
        logger.error(f"""
        Paged #{page} pages
        Current hasNextPage value: {hasNextPage}
        Previous response:
        """ + pretty_previous)
