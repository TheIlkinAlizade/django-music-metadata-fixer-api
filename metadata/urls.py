from django.urls import path

from .views import read_metadata, search_metadata, apply_metadata, auto_search

urlpatterns = [
    path("read/", read_metadata, name="read-metadata"),
    path("search/", search_metadata, name="search-metadata"),
    path("apply/", apply_metadata, name="apply-metadata"),
    path("auto-search/", auto_search, name="auto-search"),
]