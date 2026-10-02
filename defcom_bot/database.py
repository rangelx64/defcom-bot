from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import json
import sqlite3

from .config import settings
from .content import MEMBER_RANKS
from .models import ApplicationRecord, MemberRecord


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ApplicationDatabase:
    """SQLite repository for member records and application workflow."""

    def __init__(self):
        self.path = settings.state_dir / "defcom.sqlite3"

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def initialize(self) -> None:
        with closing(self._connect()) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS members (
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    birthday TEXT,
                    rank TEXT NOT NULL DEFAULT 'candidate',
                    platoon TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (guild_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    answers_json TEXT NOT NULL,
                    message_id TEXT UNIQUE,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approve', 'deny')),
                    reviewer_id TEXT,
                    created_at TEXT NOT NULL,
                    decided_at TEXT
                );
                CREATE TABLE IF NOT EXISTS guild_config (
                    guild_id TEXT NOT NULL,
                    config_key TEXT NOT NULL,
                    config_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (guild_id, config_key)
                );
                CREATE TABLE IF NOT EXISTS birthday_announcements (
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    birthday_year INTEGER NOT NULL,
                    sent_at TEXT NOT NULL,
                    PRIMARY KEY (guild_id, user_id, birthday_year)
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_pending_application_per_member
                    ON applications(guild_id, user_id) WHERE status = 'pending';
                CREATE INDEX IF NOT EXISTS members_by_platoon
                    ON members(guild_id, platoon, display_name);
            """)
            db.commit()

    @staticmethod
    def _member(row) -> MemberRecord | None:
        if row is None:
            return None
        return MemberRecord(**dict(row))

    @staticmethod
    def _application(row) -> ApplicationRecord | None:
        if row is None:
            return None
        values = dict(row)
        return ApplicationRecord(
            id=values["id"], guild_id=values["guild_id"], user_id=values["user_id"],
            username=values["username"], answers=json.loads(values["answers_json"]),
            message_id=values["message_id"], status=values["status"],
            created_at=values["created_at"],
        )

    def get_member(self, guild_id: int | str, user_id: int | str) -> MemberRecord | None:
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM members WHERE guild_id=? AND user_id=?",
                             (str(guild_id), str(user_id))).fetchone()
            return self._member(row)

    def get_guild_config(self, guild_id: int | str, key: str, default=None):
        with closing(self._connect()) as db:
            row = db.execute("SELECT config_value FROM guild_config WHERE guild_id=? AND config_key=?",
                             (str(guild_id), key)).fetchone()
        return json.loads(row["config_value"]) if row else default

    def set_guild_config(self, guild_id: int | str, key: str, value) -> None:
        with closing(self._connect()) as db:
            db.execute("""INSERT INTO guild_config(guild_id,config_key,config_value,updated_at)
                VALUES(?,?,?,?) ON CONFLICT(guild_id,config_key) DO UPDATE SET
                config_value=excluded.config_value, updated_at=excluded.updated_at""",
                (str(guild_id), key, json.dumps(value, ensure_ascii=False), _now()))
            db.commit()

    def delete_guild_config(self, guild_id: int | str, key: str) -> None:
        with closing(self._connect()) as db:
            db.execute("DELETE FROM guild_config WHERE guild_id=? AND config_key=?",
                       (str(guild_id), key))
            db.commit()

    def list_members(self, guild_id: int | str, limit: int | None = None) -> list[MemberRecord]:
        query = "SELECT * FROM members WHERE guild_id=? ORDER BY display_name COLLATE NOCASE"
        params: tuple = (str(guild_id),)
        if limit is not None:
            query += " LIMIT ?"
            params += (limit,)
        with closing(self._connect()) as db:
            return [self._member(row) for row in db.execute(query, params).fetchall()]

    def has_birthday_announcement(self, guild_id: int | str, user_id: int | str, year: int) -> bool:
        with closing(self._connect()) as db:
            return db.execute(
                "SELECT 1 FROM birthday_announcements WHERE guild_id=? AND user_id=? AND birthday_year=?",
                (str(guild_id), str(user_id), year),
            ).fetchone() is not None

    def record_birthday_announcement(self, guild_id: int | str, user_id: int | str, year: int) -> bool:
        with closing(self._connect()) as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO birthday_announcements(guild_id,user_id,birthday_year,sent_at) VALUES(?,?,?,?)",
                (str(guild_id), str(user_id), year, _now()),
            )
            db.commit()
            return cursor.rowcount == 1

    def add_member(self, *, guild_id: int | str, user_id: int | str, username: str,
                   display_name: str, birthday: str | None = None) -> bool:
        now = _now()
        with closing(self._connect()) as db:
            cursor = db.execute("""INSERT OR IGNORE INTO members
                (guild_id,user_id,username,display_name,birthday,rank,platoon,created_at,updated_at)
                VALUES (?,?,?,?,?,'candidate',NULL,?,?)""",
                (str(guild_id), str(user_id), username, display_name, birthday, now, now))
            db.commit()
            return cursor.rowcount == 1

    def remove_member(self, guild_id: int | str, user_id: int | str) -> bool:
        with closing(self._connect()) as db:
            cursor = db.execute("DELETE FROM members WHERE guild_id=? AND user_id=?",
                                (str(guild_id), str(user_id)))
            db.commit()
            return cursor.rowcount == 1

    def promote_member(self, guild_id: int | str, user_id: int | str) -> MemberRecord | None:
        member = self.get_member(guild_id, user_id)
        if member is None:
            return None
        try:
            next_rank = MEMBER_RANKS[MEMBER_RANKS.index(member.rank) + 1]
        except (ValueError, IndexError):
            return member
        self._update_member(guild_id, user_id, rank=next_rank)
        return self.get_member(guild_id, user_id)

    def set_platoon(self, guild_id: int | str, user_id: int | str, platoon: str | None) -> MemberRecord | None:
        self._update_member(guild_id, user_id, platoon=platoon)
        return self.get_member(guild_id, user_id)

    def _update_member(self, guild_id, user_id, **changes) -> None:
        allowed = {"rank", "platoon", "birthday", "username", "display_name"}
        assignments = {key: value for key, value in changes.items() if key in allowed}
        if not assignments:
            return
        assignments["updated_at"] = _now()
        setters = ", ".join(f"{key}=?" for key in assignments)
        with closing(self._connect()) as db:
            db.execute(f"UPDATE members SET {setters} WHERE guild_id=? AND user_id=?",
                       (*assignments.values(), str(guild_id), str(user_id)))
            db.commit()

    def upsert_approved_member(self, *, guild_id: int | str, user_id: int | str,
                               username: str, display_name: str, birthday: str | None) -> None:
        now = _now()
        with closing(self._connect()) as db:
            db.execute("""INSERT INTO members
                (guild_id,user_id,username,display_name,birthday,rank,platoon,created_at,updated_at)
                VALUES (?,?,?,?,?,'candidate',NULL,?,?)
                ON CONFLICT(guild_id,user_id) DO UPDATE SET
                    username=excluded.username, display_name=excluded.display_name,
                    birthday=COALESCE(excluded.birthday,members.birthday), updated_at=excluded.updated_at""",
                (str(guild_id), str(user_id), username, display_name, birthday, now, now))
            db.commit()

    def has_pending_application(self, guild_id: int | str, user_id: int | str) -> bool:
        with closing(self._connect()) as db:
            db.execute("""DELETE FROM applications WHERE guild_id=? AND user_id=?
                AND status='pending' AND message_id IS NULL
                AND datetime(created_at) < datetime('now', '-10 minutes')""",
                (str(guild_id), str(user_id)))
            db.commit()
            return db.execute("SELECT 1 FROM applications WHERE guild_id=? AND user_id=? AND status='pending'",
                              (str(guild_id), str(user_id))).fetchone() is not None

    def create_application(self, *, guild_id: int | str, user_id: int | str,
                           username: str, answers: dict[str, str]) -> int:
        with closing(self._connect()) as db:
            cursor = db.execute("""INSERT INTO applications
                (guild_id,user_id,username,answers_json,created_at)
                VALUES (?,?,?,?,?)""",
                (str(guild_id), str(user_id), username,
                 json.dumps(answers, ensure_ascii=False), _now()))
            db.commit()
            return cursor.lastrowid

    def set_application_message(self, application_id: int, message_id: int | str) -> None:
        with closing(self._connect()) as db:
            db.execute("UPDATE applications SET message_id=? WHERE id=?",
                       (str(message_id), application_id))
            db.commit()

    def delete_application(self, application_id: int) -> None:
        with closing(self._connect()) as db:
            db.execute("DELETE FROM applications WHERE id=?", (application_id,))
            db.commit()

    def get_application_by_message(self, message_id: int | str) -> ApplicationRecord | None:
        with closing(self._connect()) as db:
            return self._application(db.execute("SELECT * FROM applications WHERE message_id=?",
                                                (str(message_id),)).fetchone())

    def decide_application(self, *, message_id: int | str, decision: str,
                            reviewer_id: int | str) -> ApplicationRecord | None:
        with closing(self._connect()) as db:
            db.execute("""UPDATE applications SET status=?, reviewer_id=?, decided_at=?
                WHERE message_id=? AND status='pending'""",
                (decision, str(reviewer_id), _now(), str(message_id)))
            db.commit()
            return self._application(db.execute("SELECT * FROM applications WHERE message_id=?",
                                                (str(message_id),)).fetchone())


database = ApplicationDatabase()
