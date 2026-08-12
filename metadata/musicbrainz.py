import musicbrainzngs
import requests

musicbrainzngs.set_useragent("music-metadata-fixer", "1.0", "your-email@example.com")


def search_recording(query, fetch_covers=False, limit=5):
    result = musicbrainzngs.search_recordings(query=query, limit=limit)
    recordings = result.get("recording-list", [])

    matches = []
    for rec in recordings:
        artist = rec.get("artist-credit-phrase")
        release = rec.get("release-list", [{}])[0]
        release_id = release.get("id")

        matches.append({
            "mbid": rec.get("id"),
            "title": rec.get("title"),
            "artist": artist,
            "album": release.get("title"),
            "release_id": release_id,
            "score": rec.get("ext:score"),
            "cover_art_url": get_cover_art_url(release_id) if fetch_covers else None,
        })

    return matches


def search_recording_freetext(text, fetch_covers=False):
    result = musicbrainzngs.search_recordings(query=text, limit=5)
    recordings = result.get("recording-list", [])

    matches = []
    for rec in recordings:
        artist = rec.get("artist-credit-phrase")
        release = rec.get("release-list", [{}])[0]
        release_id = release.get("id")

        matches.append({
            "mbid": rec.get("id"),
            "title": rec.get("title"),
            "artist": artist,
            "album": release.get("title"),
            "release_id": release_id,
            "score": rec.get("ext:score"),
            "cover_art_url": get_cover_art_url(release_id) if fetch_covers else None,
        })

    return matches

def search_release(query):
    result = musicbrainzngs.search_releases(query=query, limit=5)
    releases = result.get("release-list", [])

    matches = []
    for rel in releases:
        matches.append({
            "mbid": None,
            "title": None,
            "artist": rel.get("artist-credit-phrase"),
            "album": rel.get("title"),
            "release_id": rel.get("id"),
            "score": rel.get("ext:score"),
        })

    return matches

def get_cover_art_url(release_id):
    if not release_id:
        return None

    url = f"https://coverartarchive.org/release/{release_id}"

    try:
        response = requests.get(url, timeout=5)
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    data = response.json()
    images = data.get("images", [])

    for image in images:
        if image.get("front"):
            return image.get("image")

    if images:
        return images[0].get("image")

    return None
