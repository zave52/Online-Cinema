class StubRedis:
    """Stub implementation of Redis client for testing.

    This class provides an in-memory simulation of a subset of Redis commands
    (specifically sorted sets and key expiration) to facilitate testing without
    requiring a real Redis instance. It is primarily used for testing the
    sliding window rate limiter.
    """

    def __init__(self):
        """Initialize the Redis stub with empty data and expiration stores."""
        self.data: dict[str, dict[str, float]] = {}
        self.expires = {}

    async def zremrangebyscore(self, key: str, min: float, max: float) -> int:
        """Remove all elements in a sorted set with a score between min and max.

        Args:
            key (str): The Redis key for the sorted set.
            min (float): The minimum score to remove.
            max (float): The maximum score to remove.

        Returns:
            int: The number of elements removed.
        """
        if key not in self.data:
            return 0

        to_remove = []
        for member, score in self.data[key].items():
            if min <= score <= max:
                to_remove.append(member)

        for member in to_remove:
            del self.data[key][member]

        return len(to_remove)

    async def zcard(self, key: str) -> int:
        """Get the number of members in a sorted set.

        Args:
            key (str): The Redis key for the sorted set.

        Returns:
            int: The number of elements in the sorted set, or 0 if it doesn't exist.
        """
        if key not in self.data:
            return 0
        return len(self.data[key])

    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        """Add one or more members to a sorted set, or update its score if it already exists.

        Args:
            key (str): The Redis key for the sorted set.
            mapping (dict[str, float]): A dictionary of members and their corresponding scores.

        Returns:
            int: The number of new elements added to the sorted set.
        """
        if key not in self.data:
            self.data[key] = {}

        added = 0
        for member, score in mapping.items():
            if member not in self.data[key] or self.data[key][member] != score:
                added += 1
            self.data[key][member] = score

        return added

    async def expire(self, key: str, time: int) -> bool:
        """Set a key's time to live in seconds.

        Args:
            key (str): The Redis key to set the expiration for.
            time (int): The time to live in seconds.

        Returns:
            bool: True if the timeout was set.
        """
        self.expires[key] = time
        return True

    async def aclose(self) -> None:
        """Close the Redis connection.

        This is a no-op method for the stub to satisfy the async context manager interface.
        """
        pass
