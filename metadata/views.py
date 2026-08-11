from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .services import read_tags, build_query
from .musicbrainz import search_recording, search_release


@api_view(["POST"])
def read_metadata(request):
    file_obj = request.FILES.get("file")

    if file_obj is None:
        return Response(
            {"error": "No file provided. Send it as multipart/form-data under the 'file' key."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    result = read_tags(file_obj)

    if result is None:
        return Response(
            {"error": "Could not read this file. It may be corrupted or an unsupported format."},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    return Response(result, status=status.HTTP_200_OK)


@api_view(["POST"])
def search_metadata(request):
    data = request.data

    query = build_query(
        filename=data.get("filename"),
        artist=data.get("artist"),
        title=data.get("title"),
        album=data.get("album"),
        manual_artist=data.get("manual_artist"),
        manual_title=data.get("manual_title"),
    )

    if not query:
        return Response(
            {"error": "Not enough information to search. Provide a filename, tags, or free_text."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    search_type = data.get("search_type", "track")

    if search_type == "album":
        matches = search_release(query)
    else:
        matches = search_recording(query)

    return Response({"query_used": query, "matches": matches}, status=status.HTTP_200_OK)