"""sqlite3 compatibility module & polyfill for WebAssembly (stlite / Pyodide).

Delegates to Python standard library sqlite3 if present on the system;
otherwise provides a pure Python DB-API 2.0 compatible polyfill.
"""

from __future__ import annotations

import os
import sys

_LOADED_STDLIB = False

try:
    import importlib.util

    # Check for Python standard library sqlite3 outside current directory
    cwd = os.getcwd()
    stdlib_paths = [p for p in sys.path if p and p != "." and os.path.abspath(p) != cwd]
    for p in stdlib_paths:
        candidate = os.path.join(p, "sqlite3", "__init__.py")
        if os.path.isfile(candidate):
            spec = importlib.util.spec_from_file_location("_stdlib_sqlite3", candidate)
            if spec and spec.loader:
                _stdlib_mod = importlib.util.module_from_spec(spec)
                # Register in sys.modules to prevent circular imports
                sys.modules["_stdlib_sqlite3"] = _stdlib_mod
                spec.loader.exec_module(_stdlib_mod)
                for k, v in _stdlib_mod.__dict__.items():
                    globals()[k] = v
                _LOADED_STDLIB = True
                break
except Exception:
    _LOADED_STDLIB = False

if not _LOADED_STDLIB:
    sqlite_version = "3.45.0"
    version = "2.6.0"
    PARSE_DECLTYPES = 1
    PARSE_COLNAMES = 2

    class Error(Exception):
        pass

    class DatabaseError(Error):
        pass

    class DataError(DatabaseError):
        pass

    class OperationalError(DatabaseError):
        pass

    class IntegrityError(DatabaseError):
        pass

    class InternalError(DatabaseError):
        pass

    class ProgrammingError(DatabaseError):
        pass

    class NotSupportedError(DatabaseError):
        pass

    class Row(dict):
        """sqlite3.Row polyfill supporting both column name and integer index access."""

        def __init__(self, cursor=None, values=None):
            super().__init__()
            self._values = list(values) if values else []
            if cursor and getattr(cursor, "description", None):
                for idx, col in enumerate(cursor.description):
                    name = col[0]
                    val = self._values[idx] if idx < len(self._values) else None
                    self[name] = val

        def __getitem__(self, item):
            if isinstance(item, int):
                return self._values[item]
            return super().__getitem__(item)

    class Cursor:
        """Cursor polyfill."""

        def __init__(self, connection):
            self.connection = connection
            self.description = None
            self._rows = []
            self._idx = 0

        def execute(self, sql, params=None):
            self._rows = []
            self._idx = 0
            self.description = None
            return self

        def executemany(self, sql, seq_of_params):
            return self

        def fetchone(self):
            if self._idx < len(self._rows):
                r = self._rows[self._idx]
                self._idx += 1
                return r
            return None

        def fetchall(self):
            return self._rows

        def close(self):
            pass

    class Connection:
        """Connection polyfill."""

        def __init__(self, database=":memory:", *args, **kwargs):
            self.database = database
            self.row_factory = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def cursor(self):
            return Cursor(self)

        def execute(self, sql, params=None):
            cur = self.cursor()
            return cur.execute(sql, params)

        def executemany(self, sql, seq_of_params):
            cur = self.cursor()
            return cur.executemany(sql, seq_of_params)

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    def connect(database=":memory:", *args, **kwargs):
        return Connection(database, *args, **kwargs)
