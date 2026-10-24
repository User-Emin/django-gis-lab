from rest_framework_gis.pagination import GeoJsonPagination


class KaartPaginering(GeoJsonPagination):
    page_size = 100
    max_page_size = 500

    def get_paginated_response_schema(self, view):
        schema = super().get_paginated_response_schema(view)
        # drf-gis hernoemt results -> features, maar laat 'results' in required staan
        schema["required"] = [
            ("features" if r == "results" else r) for r in schema.get("required", [])
        ]
        return schema
