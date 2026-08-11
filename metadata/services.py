from mutagen import File as MutagenFile
from mutagen.id3 import ID3, APIC
from mutagen.flac import Picture
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
import re
import requests

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
        artist = parts[0].strip()
        title = _clean_title_junk(parts[1].strip())
        return {"artist": artist, "title": title}

    return {"artist": None, "title": _clean_title_junk(name.strip())}


def _clean_title_junk(title):
    junk_patterns = [
        r"\(official\s*(video|audio|lyric\s*video|music\s*video)\)",
        r"\[official\s*(video|audio|lyric\s*video|music\s*video)\]",
        r"\(official\)",
        r"\(lyrics?\)",
        r"\[lyrics?\]",
        r"\(hd\)",
        r"\(4k\)",
        r"\(audio\)",
        r"\(visualizer\)",
    ]

    cleaned = title
    for pattern in junk_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    return cleaned.strip()


def download_cover_art(url):
    if not url:
        return None, None

    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException:
        return None, None

    if response.status_code != 200:
        return None, None

    mime_type = response.headers.get("Content-Type", "image/jpeg")
    return response.content, mime_type


def apply_tags(file_obj, filename, title=None, artist=None, album=None, date=None, cover_art_bytes=None, cover_mime=None):
    audio = MutagenFile(file_obj, easy=True)

    if audio is None:
        return None

    if title:
        audio["title"] = title
    if artist:
        audio["artist"] = artist
    if album:
        audio["album"] = album
    if date:
        audio["date"] = date

    audio.save(file_obj)

    if cover_art_bytes:
        file_obj.seek(0)
        _embed_cover_art(file_obj, filename, cover_art_bytes, cover_mime)

    file_obj.seek(0)
    return file_obj



def _embed_cover_art(file_obj, filename, image_bytes, mime_type):
    lower_name = filename.lower()

    if lower_name.endswith(".mp3"):
        _embed_cover_mp3(file_obj, image_bytes, mime_type)
    elif lower_name.endswith(".flac"):
        _embed_cover_flac(file_obj, image_bytes, mime_type)


def _embed_cover_mp3(file_obj, image_bytes, mime_type):
    audio = MP3(file_obj, ID3=ID3)

    if audio.tags is None:
        audio.add_tags()

    audio.tags.add(
        APIC(
            encoding=3,
            mime=mime_type,
            type=3,
            desc="Cover",
            data=image_bytes,
        )
    )

    audio.save(file_obj)


def _embed_cover_flac(file_obj, image_bytes, mime_type):
    audio = FLAC(file_obj)

    picture = Picture()
    picture.type = 3
    picture.mime = mime_type
    picture.data = image_bytes

    audio.clear_pictures()
    audio.add_picture(picture)
    audio.save(file_obj)