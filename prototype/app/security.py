from collections import OrderedDict
from datetime import datetime, timezone
from hashlib import sha256
from secrets import token_urlsafe
from time import monotonic
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
dummy_hash = hasher.hash(token_urlsafe(32))


def now():
    value = datetime.now(timezone.utc)
    return value.replace(microsecond=value.microsecond // 1000 * 1000)


def digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def verify(encoded: str, password: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


class LoginLimits:
    # shortcut: one process, reset on restart; replace before multiple workers.
    def __init__(self):
        self.entries = OrderedDict()

    def keys(self, login, address):
        return [("login:" + digest(login), 10), ("ip:" + digest(address), 50)]

    def blocked(self, login, address):
        stamp = monotonic()
        for key in list(self.entries):
            if stamp - self.entries[key][0] >= 900:
                del self.entries[key]
        keys = self.keys(login, address)
        if len(self.entries) >= 10000 and any(k not in self.entries for k, _ in keys):
            return True
        return any(self.entries.get(k, (stamp, 0))[1] >= limit for k, limit in keys)

    def failure(self, login, address):
        for key, _ in self.keys(login, address):
            start, count = self.entries.get(key, (monotonic(), 0))
            self.entries[key] = (start, count + 1)
