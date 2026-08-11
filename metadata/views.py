from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .services import read_tags


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