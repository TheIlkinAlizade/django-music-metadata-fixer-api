from django.urls import path

from .views import read_metadata, search_metadata, apply_metadata, auto_search, batch_auto_search, batch_apply, batch_auto_fix, get_cover_art

urlpatterns = [
    path("read/", read_metadata, name="read-metadata"),
    path("search/", search_metadata, name="search-metadata"),
    path("apply/", apply_metadata, name="apply-metadata"),
    path("auto-search/", auto_search, name="auto-search"),
    path("batch-search/", batch_auto_search, name="batch-auto-search"),
    path("batch-apply/", batch_apply, name="batch-apply"),
    path("batch-auto-fix/", batch_auto_fix, name="batch-auto-fix"),
    path("cover-art/<str:release_id>/", get_cover_art, name="get-cover-art"),
]