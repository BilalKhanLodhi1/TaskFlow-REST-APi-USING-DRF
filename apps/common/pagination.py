from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    """
    Default pagination for every list endpoint.

    Clients use ?page=2 to move between pages and may request a smaller or
    larger page with ?page_size=50, but never more than max_page_size.
    The default size comes from REST_FRAMEWORK["PAGE_SIZE"] in settings.
    """

    page_size_query_param = "page_size"
    max_page_size = 100
