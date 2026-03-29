from __future__ import annotations

from urllib import error, request


class NotificationError(RuntimeError):
    """Raised when ntfy notification delivery fails."""


class NtfyNotifier:
    def __init__(self, topic: str) -> None:
        self._url = f"https://ntfy.sh/{topic}"

    def try_send(self, title: str, message: str) -> None:
        """Send a notification, silently ignoring all delivery failures."""
        try:
            self.send(title, message)
        except NotificationError:
            pass

    def send(self, title: str, message: str) -> None:
        req = request.Request(
            self._url,
            data=message.encode("utf-8"),
            method="POST",
            headers={"Title": title},
        )
        try:
            with request.urlopen(req, timeout=20) as response:
                if response.status >= 400:
                    raise NotificationError(
                        f"ntfy returned HTTP {response.status} for title {title!r}"
                    )
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise NotificationError(
                f"ntfy send failed with {exc.code}: {details}"
            ) from exc
        except error.URLError as exc:
            raise NotificationError(f"ntfy network error: {exc}") from exc

