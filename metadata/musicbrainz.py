import musicbrainzngs

musicbrainzngs.set_useragent("music-metadata-fixer", "1.0", "your-email@example.com")


def search_recording(query):
    result = musicbrainzngs.search_recordings(query=query, limit=5)
    recordings = result.get("recording-list", [])

    matches = []
    for rec in recordings:
        artist = rec.get("artist-credit-phrase")
        release = rec.get("release-list", [{}])[0]

        matches.append({
            "mbid": rec.get("id"),
            "title": rec.get("title"),
            "artist": artist,
            "album": release.get("title"),
            "release_id": release.get("id"),
            "score": rec.get("ext:score"),
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