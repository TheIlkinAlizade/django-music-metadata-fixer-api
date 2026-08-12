import io
from django.http import FileResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .services import read_tags, build_query, apply_tags, download_cover_art, parse_filename
from .musicbrainz import search_recording, search_release, search_recording_freetext, get_cover_art_url

import json
import zipfile
import re


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
    free_text = data.get("free_text")

    if free_text:
        matches = search_recording_freetext(free_text.strip())
        return Response({"query_used": free_text.strip(), "matches": matches}, status=status.HTTP_200_OK)

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
            {"error": "Not enough info. Provide a filename, tags, manual_artist/manual_title, or free_text."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    search_type = data.get("search_type", "track")
    matches = search_release(query) if search_type == "album" else search_recording(query)

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

    attempted_queries = [query]
    matches = search_release(query) if search_type == "album" else search_recording(query)

    if not matches and "(" in query:
        stripped = re.sub(r"\([^)]*\)", "", query).strip()
        if stripped != query:
            attempted_queries.append(stripped)
            matches = search_recording(stripped)
            if matches:
                query = stripped

    if not matches:
        raw_text = filename
        raw_text = re.sub(r"\.\w+$", "", raw_text)
        raw_text = re.sub(r"\([^)]*\)", "", raw_text)
        raw_text = re.sub(r"\[[^\]]*\]", "", raw_text)
        raw_text = raw_text.strip(" -_")

        if raw_text:
            attempted_queries.append(raw_text)
            matches = search_recording_freetext(raw_text)
            if matches:
                query = raw_text

    if not matches and not (tags.get("artist") and tags.get("title")):
        parsed = parse_filename(filename)
        if parsed["artist"] and parsed["title"]:
            swapped_query = f'artist:"{parsed["title"]}" AND recording:"{parsed["artist"]}"'
            attempted_queries.append(swapped_query)
            matches = search_recording(swapped_query)
            if matches:
                query = swapped_query

    return Response(
        {
            "existing_tags": read_result,
            "query_used": query,
            "matches": matches,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def batch_auto_search(request):
    files = request.FILES.getlist("files")

    if not files:
        return Response(
            {"error": "No files provided. Send them as multipart/form-data under the 'files' key (multiple allowed)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    results = []

    for file_obj in files:
        filename = file_obj.name

        try:
            read_result = read_tags(file_obj)

            if read_result is None:
                results.append({
                    "filename": filename,
                    "status": "error",
                    "error": "Could not read this file. It may be corrupted or an unsupported format.",
                })
                continue

            tags = read_result["tags"]

            query = build_query(
                filename=filename,
                artist=tags.get("artist"),
                title=tags.get("title"),
                album=tags.get("album"),
            )

            if not query:
                results.append({
                    "filename": filename,
                    "status": "no_query",
                    "existing_tags": read_result,
                    "matches": [],
                })
                continue

            matches = search_recording(query)

            results.append({
                "filename": filename,
                "status": "ok",
                "existing_tags": read_result,
                "query_used": query,
                "matches": matches,
            })

        except Exception as exc:
            results.append({
                "filename": filename,
                "status": "error",
                "error": str(exc),
            })

    return Response({"results": results}, status=status.HTTP_200_OK)


def sanitize_filename(name):
    invalid_chars = '<>:"/\\|?*'
    for ch in invalid_chars:
        name = name.replace(ch, "")
    return name.strip()


@api_view(["POST"])
def batch_apply(request):
    files = request.FILES.getlist("files")
    metadata_json = request.data.get("metadata")

    if not files:
        return Response(
            {"error": "No files provided. Send them as multipart/form-data under the 'files' key (multiple allowed)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not metadata_json:
        return Response(
            {"error": "Missing 'metadata' field. Send a JSON array with one entry per file, in the same order."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        metadata_list = json.loads(metadata_json)
    except (json.JSONDecodeError, TypeError):
        return Response(
            {"error": "'metadata' must be a valid JSON array."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(metadata_list) != len(files):
        return Response(
            {"error": f"Got {len(files)} files but {len(metadata_list)} metadata entries. They must match 1:1, in order."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    zip_buffer = io.BytesIO()
    errors = []

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_obj, meta in zip(files, metadata_list):
            original_filename = file_obj.name

            try:
                title = meta.get("title")
                artist = meta.get("artist")
                album = meta.get("album")
                date = meta.get("date")
                cover_art_url = meta.get("cover_art_url")

                file_bytes = file_obj.read()
                buffer = io.BytesIO(file_bytes)

                cover_art_bytes, cover_mime = download_cover_art(cover_art_url)

                result = apply_tags(
                    buffer,
                    original_filename,
                    title=title,
                    artist=artist,
                    album=album,
                    date=date,
                    cover_art_bytes=cover_art_bytes,
                    cover_mime=cover_mime,
                )

                if result is None:
                    errors.append({"filename": original_filename, "error": "Could not process this file."})
                    continue

                extension = original_filename.split(".")[-1]

                if artist and title:
                    new_filename = sanitize_filename(f"{artist} - {title}.{extension}")
                else:
                    new_filename = original_filename

                result.seek(0)
                zip_file.writestr(new_filename, result.read())

            except Exception as exc:
                errors.append({"filename": original_filename, "error": str(exc)})

    zip_buffer.seek(0)

    response = FileResponse(zip_buffer, as_attachment=True, filename="fixed_music.zip")
    response["X-Batch-Errors"] = json.dumps(errors)
    return response


@api_view(["POST"])
def batch_auto_fix(request):
    files = request.FILES.getlist("files")

    if not files:
        return Response(
            {"error": "No files provided. Send them as multipart/form-data under the 'files' key (multiple allowed)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    zip_buffer = io.BytesIO()
    errors = []
    skipped = []

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_obj in files:
            original_filename = file_obj.name

            try:
                read_result = read_tags(file_obj)

                if read_result is None:
                    errors.append({"filename": original_filename, "error": "Could not read this file."})
                    continue

                tags = read_result["tags"]

                query = build_query(
                    filename=original_filename,
                    artist=tags.get("artist"),
                    title=tags.get("title"),
                    album=tags.get("album"),
                )

                if not query:
                    skipped.append({"filename": original_filename, "reason": "Not enough info to search automatically."})
                    file_obj.seek(0)
                    zip_file.writestr(original_filename, file_obj.read())
                    continue

                matches = search_recording(query, fetch_covers=True)

                if not matches and "(" in query:
                    stripped = re.sub(r"\([^)]*\)", "", query).strip()
                    if stripped != query:
                        matches = search_recording(stripped, fetch_covers=True)
                        if matches:
                            query = stripped

                if not matches:
                    raw_text = re.sub(r"\.\w+$", "", original_filename)
                    raw_text = re.sub(r"\([^)]*\)", "", raw_text)
                    raw_text = re.sub(r"\[[^\]]*\]", "", raw_text)
                    raw_text = raw_text.strip(" -_")
                    if raw_text:
                        matches = search_recording_freetext(raw_text, fetch_covers=True)
                        if matches:
                            query = raw_text

                if not matches:
                    parsed = parse_filename(original_filename)
                    if parsed["artist"] and parsed["title"]:
                        swapped_query = f'artist:"{parsed["title"]}" AND recording:"{parsed["artist"]}"'
                        matches = search_recording(swapped_query, fetch_covers=True)

                if not matches:
                    skipped.append({"filename": original_filename, "reason": "No matches found."})
                    file_obj.seek(0)
                    zip_file.writestr(original_filename, file_obj.read())
                    continue

                best_match = matches[0]

                title = best_match.get("title")
                artist = best_match.get("artist")
                album = best_match.get("album")
                cover_art_url = best_match.get("cover_art_url")

                file_obj.seek(0)
                file_bytes = file_obj.read()
                buffer = io.BytesIO(file_bytes)

                cover_art_bytes, cover_mime = download_cover_art(cover_art_url)

                result = apply_tags(
                    buffer,
                    original_filename,
                    title=title,
                    artist=artist,
                    album=album,
                    cover_art_bytes=cover_art_bytes,
                    cover_mime=cover_mime,
                )

                if result is None:
                    errors.append({"filename": original_filename, "error": "Could not process this file."})
                    continue

                extension = original_filename.split(".")[-1]
                new_filename = sanitize_filename(f"{artist} - {title}.{extension}")

                result.seek(0)
                zip_file.writestr(new_filename, result.read())

            except Exception as exc:
                errors.append({"filename": original_filename, "error": str(exc)})

    zip_buffer.seek(0)

    response = FileResponse(zip_buffer, as_attachment=True, filename="auto_fixed_music.zip")
    response["X-Batch-Errors"] = json.dumps(errors)
    response["X-Batch-Skipped"] = json.dumps(skipped)
    return response


@api_view(["GET"])
def get_cover_art(request, release_id):
    url = get_cover_art_url(release_id)
    return Response({"cover_art_url": url}, status=status.HTTP_200_OK)