from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomPagination(PageNumberPagination):
		page_size = 10  # Default page size
		max_page_size = 100  # Maximum page size to prevent abuse
		page_size_query_param = 'size'  # Allow client to set page size
		page_query_param = 'page'  # Page query parameter

		def get_paginated_response(self, data):
			return Response(
				{
					"count": self.page.paginator.count,
					"total": self.page.paginator.num_pages,
					"page": self.page.number,
					"results": data,
				}
			)