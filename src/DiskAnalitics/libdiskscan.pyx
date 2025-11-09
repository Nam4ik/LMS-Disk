
import ctypes
from ctypes import wintypes
from cpython.ref cimport PyObject
import os
import sys
import sqlite3
from time import time

from typing import Dict, Tuple

cdef class Entry:
    cdef public object path
    cdef public unsigned long long size
    cdef public object type  
    cdef public double mtime

    def __init__(self, path, size, type_, mtime):
        self.path = path
        self.size = size
        self.type = type_
        self.mtime = mtime


def _stat_size_and_mtime(path, follow_symlinks=False):
    try:
        st = os.stat(path, follow_symlinks=follow_symlinks)
        return st.st_size, st.st_mtime
    except Exception:
        return 0, 0.0


def scan(path: str, follow_symlinks: bool=False, max_depth: int=-1):

    cdef dict result = {}
    cdef list stack = []  
    cdef object it
    cdef object entry
    cdef str full
    cdef unsigned long long fsize
    cdef double mtime
    cdef object etype

    root = os.path.abspath(path)
    stack.append((root, 0))

    cdef dict dir_children = {}

    while stack:
        dirpath, depth = stack.pop()
 
        try:
            it = os.scandir(dirpath)
        except Exception as e:
            fsize, mtime = _stat_size_and_mtime(dirpath, follow_symlinks)
            result[dirpath] = (fsize, 'file', mtime)
            continue
        try:
            for entry in it:
                full = os.path.join(dirpath, entry.name)
                try:
                    if entry.is_symlink():
                        if follow_symlinks:
                            fsize, mtime = _stat_size_and_mtime(full, True)
                            try:
                                if os.path.isdir(full):
                                    stack.append((full, depth + 1))
                                    result[full] = (0, 'dir', mtime)
                                else:
                                    result[full] = (fsize, 'file', mtime)
                            except Exception:
                                result[full] = (fsize, 'file', mtime)
                        else:
                            result[full] = (0, 'link', time())
                    elif entry.is_dir(follow_symlinks=False):
                        stack.append((full, depth + 1))
                        result[full] = (0, 'dir', entry.stat(follow_symlinks=False).st_mtime if hasattr(entry, 'stat') else 0.0)
                    elif entry.is_file(follow_symlinks=False):
                        try:
                            st = entry.stat(follow_symlinks=False)
                            fsize = st.st_size
                            mtime = st.st_mtime
                        except Exception:
                            fsize, mtime = _stat_size_and_mtime(full, False)
                        result[full] = (fsize, 'file', mtime)
                    else:
                        try:
                            st = entry.stat(follow_symlinks=False)
                            fsize = st.st_size
                            mtime = st.st_mtime
                        except Exception:
                            fsize, mtime = 0, 0.0
                        result[full] = (fsize, 'unknown', mtime)
                except PermissionError:
                    # skip
                    continue
        finally:
            try:
                it.close()
            except Exception:
                pass 
            
    paths = sorted(result.keys(), key=lambda p: -len(p))
    for p in paths:
        size, t, mtime = result[p]
        if t == 'file':
            parent = os.path.dirname(p)
            while parent and parent in result:
                psize, pt, pmt = result[parent]
                result[parent] = (psize + size, pt, pmt)
                parent = os.path.dirname(parent)
    return result


def get_fs_type(path: str) -> str:
    if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        try:
            mounts = []
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3:
                        device = parts[0]
                        mpoint = parts[1]
                        fstype = parts[2]
                        mounts.append((mpoint, fstype))
            mounts.sort(key=lambda x: -len(x[0]))
            abs_path = os.path.abspath(path)
            for mpoint, fstype in mounts:
                if abs_path.startswith(mpoint.rstrip('/')):
                    return fstype
        except Exception:
            pass
        try:
            st = os.statvfs(path)
            return 'unknown'
        except Exception:
            return 'unknown'
    elif sys.platform.startswith('win'):
        try:
            GetVolumePathNameW = ctypes.windll.kernel32.GetVolumePathNameW
            GetVolumePathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
            GetVolumeInformationW = ctypes.windll.kernel32.GetVolumeInformationW
            GetVolumeInformationW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
                                             wintypes.LPDWORD, wintypes.LPDWORD, wintypes.LPDWORD, wintypes.LPWSTR, wintypes.DWORD]
            buffer_len = 260
            vol_name_buf = ctypes.create_unicode_buffer(buffer_len)
            fs_name_buf = ctypes.create_unicode_buffer(buffer_len)
            root_path_buf = ctypes.create_unicode_buffer(buffer_len)
            res = GetVolumePathNameW(path, root_path_buf, buffer_len)
            if res == 0:
                return 'unknown'
            res2 = GetVolumeInformationW(root_path_buf, vol_name_buf, buffer_len, None, None, None, fs_name_buf, buffer_len)
            if res2 == 0:
                return 'unknown'
            return fs_name_buf.value
        except Exception:
            return 'unknown'
    else:
        return 'unknown'


def save_snapshot(db_path: str, snapshot_name: str, entries: dict) -> None:
    """
    Save snapshot into sqlite3 database.
    Schema (created if missing):
    CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, name TEXT, created REAL);
    CREATE TABLE IF NOT EXISTS entries (snapshot_id INTEGER, path TEXT, size INTEGER, type TEXT, mtime REAL, PRIMARY KEY(snapshot_id, path));
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, name TEXT UNIQUE, created REAL)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS entries (snapshot_id INTEGER, path TEXT, size INTEGER, type TEXT, mtime REAL, PRIMARY KEY(snapshot_id, path))''')
    now = time()
    try:
        cur.execute('INSERT INTO snapshots (name, created) VALUES (?,?)', (snapshot_name, now))
    except sqlite3.IntegrityError:
        cur.execute('SELECT id FROM snapshots WHERE name=?', (snapshot_name,))
        row = cur.fetchone()
        if row:
            snapshot_id = row[0]
            cur.execute('UPDATE snapshots SET created=? WHERE id=?', (now, snapshot_id))
        else:
            cur.execute('INSERT OR REPLACE INTO snapshots (name, created) VALUES (?,?)', (snapshot_name, now))
    conn.commit()
    cur.execute('SELECT id FROM snapshots WHERE name=?', (snapshot_name,))
    snapshot_id = cur.fetchone()[0]

    to_insert = []
    for path, (size, t, mtime) in entries.items():
        to_insert.append((snapshot_id, path, int(size), t, float(mtime)))
    cur.executemany('INSERT OR REPLACE INTO entries (snapshot_id, path, size, type, mtime) VALUES (?,?,?,?,?)', to_insert)
    conn.commit()
    conn.close()
