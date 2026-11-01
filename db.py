import sqlite3
from datetime import datetime

FIELDS = ('title', 'body', 'link', 'img1', 'img2', 'event_date')


class Database:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            '''CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                link TEXT NOT NULL DEFAULT '',
                img1 TEXT NOT NULL DEFAULT '',
                img2 TEXT NOT NULL DEFAULT '',
                event_date TEXT NOT NULL DEFAULT '',
                pinned INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )'''
        )
        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS profile (key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT "")'
        )
        self.conn.commit()

    def get_profile(self):
        rows = self.conn.execute('SELECT key, value FROM profile').fetchall()
        return {r['key']: r['value'] for r in rows}

    def set_profile(self, **data):
        for k, v in data.items():
            self.conn.execute('INSERT OR REPLACE INTO profile (key, value) VALUES (?, ?)', (k, v))
        self.conn.commit()

    def count(self, kind=None, saved_only=False):
        sql, args, where = 'SELECT COUNT(*) FROM entries', [], []
        if kind:
            where.append('kind = ?')
            args.append(kind)
        if saved_only:
            where.append('pinned = 1')  # 'pinned' column ही "Saved" है
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        return self.conn.execute(sql, args).fetchone()[0]

    def add(self, kind, **data):
        vals = [data.get(f, '') for f in FIELDS]
        now = datetime.now().isoformat(timespec='seconds')
        cur = self.conn.execute(
            'INSERT INTO entries (kind, %s, created_at) VALUES (?, %s, ?)'
            % (', '.join(FIELDS), ', '.join('?' * len(FIELDS))),
            [kind] + vals + [now],
        )
        self.conn.commit()
        return cur.lastrowid

    def update(self, entry_id, **data):
        cols = [f for f in FIELDS if f in data]
        if not cols:
            return
        self.conn.execute(
            'UPDATE entries SET %s WHERE id = ?' % ', '.join(c + ' = ?' for c in cols),
            [data[c] for c in cols] + [entry_id],
        )
        self.conn.commit()

    def delete(self, entry_id):
        self.conn.execute('DELETE FROM entries WHERE id = ?', (entry_id,))
        self.conn.commit()

    def toggle_pin(self, entry_id):
        self.conn.execute(
            'UPDATE entries SET pinned = 1 - pinned WHERE id = ?', (entry_id,))
        self.conn.commit()

    def get_all(self, kind=None, query='', saved_only=False, limit=None,
                by_event_date=False):
        where, args = [], []
        if kind:
            where.append('kind = ?')
            args.append(kind)
        if saved_only:
            where.append('pinned = 1')
        q = query.strip()
        if q:
            like = '%' + q + '%'
            where.append('(title LIKE ? OR body LIKE ? OR link LIKE ? OR event_date LIKE ?)')
            args += [like] * 4
        sql = 'SELECT * FROM entries'
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        if by_event_date and kind == 'event':
            sql += ' ORDER BY event_date ASC, created_at DESC'
        else:
            sql += ' ORDER BY created_at DESC, id DESC'
        if limit:
            sql += ' LIMIT %d' % int(limit)
        return self.conn.execute(sql, args).fetchall()
