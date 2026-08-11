from mutagen import File as MutagenFile
import re


def read_tags(file_obj):
    audio = MutagenFile(file_obj, easy=True)

    if audio is None:
        return None

    tags = {
        "title": audio.get("title", [None])[0],
        "artist": audio.get("artist", [None])[0],
        "album": audio.get("album", [None])[0],
        "date": audio.get("date", [None])[0],
        "tracknumber": audio.get("tracknumber", [None])[0],
    }

    has_cover_art = _has_embedded_cover(file_obj)

    return {
        "tags": tags,
        "has_cover_art": has_cover_art,
        "format": audio.mime[0] if audio.mime else None,
        "length_seconds": round(audio.info.length, 2) if audio.info else None,
    }


def _has_embedded_cover(file_obj):
    file_obj.seek(0)
    audio = MutagenFile(file_obj)

    if audio is None:
        return False

    if hasattr(audio, "pictures") and audio.pictures:
        return True

    if audio.tags:
        for key in audio.tags.keys():
            if key.startswith("APIC"):
                return True

    return False

def build_query(filename=None, artist=None, title=None, album=None, manual_artist=None, manual_title=None):
    if manual_artist and manual_title:
        return f'artist:"{manual_artist}" AND recording:"{manual_title}"'

    if manual_title:
        return f'recording:"{manual_title}"'

    if artist and title:
        return f'artist:"{artist}" AND recording:"{title}"'

    if title:
        return f'recording:"{title}"'

    if filename:
        parsed = parse_filename(filename)
        if parsed["artist"] and parsed["title"]:
            return f'artist:"{parsed["artist"]}" AND recording:"{parsed["title"]}"'
        if parsed["title"]:
            return f'recording:"{parsed["title"]}"'

    return None

def parse_filename(filename):
    name = re.sub(r"\.\w+$", "", filename)
    name = re.sub(r"^\d+[\s\-\.]+", "", name)

    if " - " in name:
        parts = name.split(" - ", 1)
        return {"artist": parts[0].strip(), "title": parts[1].strip()}

    return {"artist": None, "title": name.strip()}