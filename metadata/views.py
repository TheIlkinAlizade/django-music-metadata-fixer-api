import io
from django.http import FileResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .services import read_tags, build_query, apply_tags, download_cover_art
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


@api_view(["POST"])
def apply_metadata(request):
    file_obj = request.FILES.get("file")

    if file_obj is None:
        return Response(
            {"error": "No file provided. Send it as multipart/form-data under the 'file' key."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    filename = file_obj.name
    title = request.data.get("title")
    artist = request.data.get("artist")
    album = request.data.get("album")
    date = request.data.get("date")
    cover_art_url = request.data.get("cover_art_url")

    file_bytes = file_obj.read()
    buffer = io.BytesIO(file_bytes)

    cover_art_bytes, cover_mime = download_cover_art(cover_art_url)

    result = apply_tags(
        buffer,
        filename,
        title=title,
        artist=artist,
        album=album,
        date=date,
        cover_art_bytes=cover_art_bytes,
        cover_mime=cover_mime,
    )

    if result is None:
        return Response(
            {"error": "Could not process this file. It may be corrupted or an unsupported format."},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    result.seek(0)
    return FileResponse(result, as_attachment=True, filename=filename)



@api_view(["POST"])
def auto_search(request):
    file_obj = request.FILES.get("file")

    if file_obj is None:
        return Response(
            {"error": "No file provided. Send it as multipart/form-data under the 'file' key."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    filename = file_obj.name
    read_result = read_tags(file_obj)

    if read_result is None:
        return Response(
            {"error": "Could not read this file. It may be corrupted or an unsupported format."},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    tags = read_result["tags"]

    query = build_query(
        filename=filename,
        artist=tags.get("artist"),
        title=tags.get("title"),
        album=tags.get("album"),
    )

    if not query:
        return Response(
            {
                "existing_tags": read_result,
                "query_used": None,
                "matches": [],
                "message": "Not enough information found to search automatically. Try manual search.",
            },
            status=status.HTTP_200_OK,
        )

    search_type = request.data.get("search_type", "track")

    if search_type == "album":
        matches = search_release(query)
    else:
        matches = search_recording(query)

    return Response(
        {
            "existing_tags": read_result,
            "query_used": query,
            "matches": matches,
        },
        status=status.HTTP_200_OK,
    )