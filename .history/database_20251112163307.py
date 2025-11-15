import os
import sqlite3
import uuid
import hashlib
from typing import Optional, List, Dict, Any

import pandas as pd

DB_PATH = "therapy.db"

TARGET_MOODS = [
    "calm",
    "happy",
    "focused",
    "energized",
    "relaxed",
]


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(cur: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    cur.execute(f"PRAGMA table_info({table});")
    columns = {row[1] for row in cur.fetchall()}
    if column not in columns:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition};")


def init_db() -> None:
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS therapists (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            practice_name TEXT,
            license_number TEXT
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS parents (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY,
            child_name TEXT NOT NULL,
            dob DATE,
            therapist_id INTEGER,
            default_target_mood TEXT NOT NULL DEFAULT 'calm',
            FOREIGN KEY(therapist_id) REFERENCES therapists(id)
        );
        """
    )

    _ensure_column(cur, "profiles", "dob", "DATE")
    _ensure_column(cur, "profiles", "therapist_id", "INTEGER")
    _ensure_column(cur, "profiles", "default_target_mood", "TEXT NOT NULL DEFAULT 'calm'")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS profile_access (
            parent_id INTEGER NOT NULL,
            profile_id INTEGER NOT NULL,
            PRIMARY KEY (parent_id, profile_id),
            FOREIGN KEY(parent_id) REFERENCES parents(id),
            FOREIGN KEY(profile_id) REFERENCES profiles(id)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS parent_invites (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(profile_id) REFERENCES profiles(id)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS session_history (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            start_mood TEXT,
            target_mood TEXT,
            feedback_emoji TEXT,
            playlist_json TEXT,
            FOREIGN KEY(profile_id) REFERENCES profiles(id)
        );
        """
    )

    cur.execute(
        """
        UPDATE profiles
        SET default_target_mood = 'calm'
        WHERE default_target_mood IS NULL;
        """
    )

    conn.commit()
    conn.close()


def _hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def _verify_password(password: str, stored: str) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, digest = stored.split("$", 1)
    candidate = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
    return candidate == digest


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def create_therapist(
    *,
    name: str,
    email: str,
    password: str,
    practice_name: Optional[str] = None,
    license_number: Optional[str] = None,
) -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO therapists (name, email, password_hash, practice_name, license_number)
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                name.strip(),
                email.strip().lower(),
                _hash_password(password),
                practice_name.strip() if practice_name else None,
                license_number.strip() if license_number else None,
            ),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError as exc:
        raise ValueError("A therapist with this email already exists.") from exc
    finally:
        conn.close()


def get_therapist_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        row = cur.execute(
            "SELECT * FROM therapists WHERE email = ?;",
            (email.strip().lower(),),
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def authenticate_therapist(email: str, password: str) -> Optional[Dict[str, Any]]:
    therapist = get_therapist_by_email(email)
    if therapist and _verify_password(password, therapist["password_hash"]):
        return therapist
    return None


def get_parent_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        row = cur.execute(
            "SELECT * FROM parents WHERE email = ?;",
            (email.strip().lower(),),
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def authenticate_parent(email: str, password: str) -> Optional[Dict[str, Any]]:
    parent = get_parent_by_email(email)
    if parent and _verify_password(password, parent["password_hash"]):
        return parent
    return None


def create_profile(
    *,
    child_name: str,
    dob: Optional[str],
    default_target_mood: str,
    therapist_id: int,
) -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO profiles (child_name, dob, default_target_mood, therapist_id)
            VALUES (?, ?, ?, ?);
            """,
            (
                child_name.strip(),
                dob,
                default_target_mood,
                therapist_id,
            ),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError as exc:
        raise ValueError(
            "A child profile with this name already exists. Please choose a unique identifier."
        ) from exc
    finally:
        conn.close()


def get_profile(profile_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        row = cur.execute(
            "SELECT * FROM profiles WHERE id = ?;",
            (profile_id,),
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_profiles_for_therapist(therapist_id: int) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        rows = cur.execute(
            """
            SELECT p.*, COUNT(pa.parent_id) AS parent_count
            FROM profiles p
            LEFT JOIN profile_access pa ON pa.profile_id = p.id
            WHERE p.therapist_id = ?
            GROUP BY p.id
            ORDER BY p.child_name ASC;
            """,
            (therapist_id,),
        ).fetchall()
        return [_row_to_dict(row) or {} for row in rows]
    finally:
        conn.close()


def get_profiles_for_parent(parent_id: int) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        rows = cur.execute(
            """
            SELECT p.*
            FROM profiles p
            JOIN profile_access pa ON pa.profile_id = p.id
            WHERE pa.parent_id = ?
            ORDER BY p.child_name ASC;
            """,
            (parent_id,),
        ).fetchall()
        return [_row_to_dict(row) or {} for row in rows]
    finally:
        conn.close()


def get_parents_for_profile(profile_id: int) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        rows = cur.execute(
            """
            SELECT pr.*
            FROM parents pr
            JOIN profile_access pa ON pa.parent_id = pr.id
            WHERE pa.profile_id = ?
            ORDER BY pr.name ASC;
            """,
            (profile_id,),
        ).fetchall()
        return [_row_to_dict(row) or {} for row in rows]
    finally:
        conn.close()


def link_parent_to_profile(parent_id: int, profile_id: int) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT OR IGNORE INTO profile_access (parent_id, profile_id)
            VALUES (?, ?);
            """,
            (parent_id, profile_id),
        )
        conn.commit()
    finally:
        conn.close()


def create_parent_invite(profile_id: int, email: str) -> str:
    token = uuid.uuid4().hex
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO parent_invites (profile_id, email, token)
            VALUES (?, ?, ?);
            """,
            (profile_id, email.strip().lower(), token),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_invite_by_token(token: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        row = cur.execute(
            """
            SELECT * FROM parent_invites
            WHERE token = ?;
            """,
            (token,),
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def list_invites_for_profile(profile_id: int) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        rows = cur.execute(
            """
            SELECT * FROM parent_invites
            WHERE profile_id = ?
            ORDER BY created_at DESC;
            """,
            (profile_id,),
        ).fetchall()
        return [_row_to_dict(row) or {} for row in rows]
    finally:
        conn.close()


def complete_parent_invite(token: str, name: str, password: str) -> Dict[str, Any]:
    invite = get_invite_by_token(token)
    if not invite:
        raise ValueError("Invitation not found. Please check the link provided by the therapist.")
    if invite["status"] != "pending":
        raise ValueError("This invitation has already been used.")

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        parent = get_parent_by_email(invite["email"])
        if parent is None:
            cur.execute(
                """
                INSERT INTO parents (name, email, password_hash)
                VALUES (?, ?, ?);
                """,
                (
                    name.strip(),
                    invite["email"],
                    _hash_password(password),
                ),
            )
            parent_id = cur.lastrowid
        else:
            parent_id = parent["id"]

        cur.execute(
            """
            INSERT OR IGNORE INTO profile_access (parent_id, profile_id)
            VALUES (?, ?);
            """,
            (parent_id, invite["profile_id"]),
        )

        cur.execute(
            """
            UPDATE parent_invites
            SET status = 'accepted'
            WHERE token = ?;
            """,
            (token,),
        )
        conn.commit()

        refreshed = get_parent_by_email(invite["email"])
        if refreshed is None:
            raise ValueError("Parent account could not be created. Please contact support.")
        return refreshed
    finally:
        conn.close()


def save_session(
    profile_id: int,
    start_mood: str,
    target_mood: str,
    feedback_emoji: Optional[str],
    playlist_json: str,
) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO session_history (profile_id, start_mood, target_mood, feedback_emoji, playlist_json)
            VALUES (?, ?, ?, ?, ?);
            """,
            (profile_id, start_mood, target_mood, feedback_emoji, playlist_json),
        )
        conn.commit()
    finally:
        conn.close()


def get_history(profile_id: int) -> pd.DataFrame:
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(
            """
            SELECT timestamp, start_mood, target_mood, feedback_emoji, playlist_json
            FROM session_history
            WHERE profile_id = ?
            ORDER BY timestamp ASC;
            """,
            conn,
            params=(profile_id,),
        )
        return df
    finally:
        conn.close()
