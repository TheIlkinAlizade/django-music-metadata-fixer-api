from django.urls import path

from .views import read_metadata, search_metadata

urlpatterns = [
    path("read/", read_metadata, name="read-metadata"),
    path("search/", search_metadata, name="search-metadata"),
]