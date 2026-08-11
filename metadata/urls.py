from django.urls import path

from .views import read_metadata

urlpatterns = [
    path("read/", read_metadata, name="read-metadata"),
]