from datetime import datetime, timezone


class InMemoryStorage:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Remove all data. Used by the tests to start from a clean state."""
        # Each dictionary maps an integer id to a record (a plain dict).
        self.trackers: dict[int, dict] = {}
        self.posts: dict[int, dict] = {}
        self.matches: dict[int, dict] = {}
        self.notifications: dict[int, dict] = {}
        self._last_ids: dict[str, int] = {
            "tracker": 0,
            "post": 0,
            "match": 0,
            "notification": 0,
        }

    def next_id(self, kind: str) -> int:
        """Return a new unique id for the given kind of record."""
        self._last_ids[kind] += 1
        return self._last_ids[kind]


def now() -> datetime:
    """Current time in UTC. Used for created_at / updated_at fields."""
    return datetime.now(timezone.utc)


# The single shared storage instance used by the whole application.
storage = InMemoryStorage()
