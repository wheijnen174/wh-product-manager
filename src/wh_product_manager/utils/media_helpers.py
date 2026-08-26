import mimetypes
import urllib.request


def _clean_content_type(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(";", 1)[0].strip().lower() or None


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def mime_and_size_from_url(
    url: str,
    precise_result: bool = False,
    timeout: float = 10.0,
    sniff_bytes: int = 2048,
) -> tuple[str | None, int | None]:
    """
    Returns (mime_type, size_bytes).

    - size_bytes is taken from Content-Length when available.
    - If the server supports Range requests, size may be derived from Content-Range.
    - If neither is available, size_bytes is None.
    """
    mime: str | None = None
    size: int | None = None

    if precise_result:
        # 1) HEAD: best for both Content-Type and Content-Length without downloading
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                mime = _clean_content_type(resp.headers.get("Content-Type"))
                size = _parse_int(resp.headers.get("Content-Length"))

                # If server provides a meaningful mime and a size, we can return early.
                if mime and mime != "application/octet-stream" and size is not None:
                    return mime, size
                # Otherwise keep what we learned and try sniffing.
        except Exception:
            pass

        # 2) Sniff first bytes (+ try to derive total size from Content-Range)
        try:
            req = urllib.request.Request(
                url, headers={"Range": f"bytes=0-{sniff_bytes - 1}"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                # Size: prefer Content-Range total if present: "bytes 0-2047/12345"
                if size is None:
                    content_range = resp.headers.get("Content-Range")
                    if content_range and "/" in content_range:
                        total = content_range.split("/", 1)[1].strip()
                        if total.isdigit():
                            size = int(total)

                # Fallback: Content-Length here is only the partial length when using Range.
                prefix = resp.read(sniff_bytes)

            # MIME sniffing (optional)
            if not mime or mime == "application/octet-stream":
                try:
                    import magic  # pip install python-magic (plus libmagic on many OSes)

                    guessed = magic.from_buffer(prefix, mime=True)
                    mime = _clean_content_type(guessed) or mime
                except Exception:
                    pass
        except Exception:
            pass

    # 3) Extension fallback for MIME only
    if not mime or mime == "application/octet-stream":
        guessed_mime, _ = mimetypes.guess_type(url)
        mime = guessed_mime or mime

    return mime, size
