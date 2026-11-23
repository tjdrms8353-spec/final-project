"""Process lock on this machine; OS releases it even after a process crash."""
import hashlib
import os
from contextlib import contextmanager
from pathlib import Path


class CollectionBusy(RuntimeError):
    pass


@contextmanager
def collection_lock(feed):
    directory = Path(__file__).resolve().parents[2] / '.cache' / 'collection-locks'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (hashlib.sha256(feed.encode()).hexdigest() + '.lock')
    with path.open('a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise CollectionBusy('Collection already running') from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
