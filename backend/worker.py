"""后台 worker：用 SKIP LOCKED 认领 pending 记录并写入判定结论。"""

import os
import time
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row

from db import ADD_DONE_VERDICT_CONSTRAINT, SCHEMA, connect
from rules import judge

POLL_SEC = float(os.environ.get("WORKER_POLL_SEC", "0.5"))
IDLE_SEC = float(os.environ.get("WORKER_IDLE_SEC", "1.0"))


def ensure_schema(conn):
    conn.execute(SCHEMA)
    conn.commit()


def repair_half_states(conn) -> int:
    """修复历史半态：status=done 却没有结论的行，按误差重新判定补写。"""
    rows = conn.execute(
        """SELECT id, yaw_err_deg
           FROM yaw_logs
           WHERE status = 'done' AND (verdict IS NULL OR verdict = '')"""
    ).fetchall()
    now = datetime.now(timezone.utc)
    for row in rows:
        verdict, reason = judge(float(row["yaw_err_deg"]))
        conn.execute(
            """UPDATE yaw_logs
               SET verdict = %s, reason = %s,
                   processed_at = COALESCE(processed_at, %s)
               WHERE id = %s""",
            (verdict, reason, now, row["id"]),
        )
    return len(rows)


def claim_and_process(conn) -> bool:
    with conn.transaction():
        row = conn.execute(
            """SELECT id, turbine_code, yaw_err_deg
               FROM yaw_logs
               WHERE status = 'pending'
               ORDER BY id
               FOR UPDATE SKIP LOCKED
               LIMIT 1"""
        ).fetchone()
        if row is None:
            return False
        verdict, reason = judge(float(row["yaw_err_deg"]))
        now = datetime.now(timezone.utc)
        conn.execute(
            """UPDATE yaw_logs
               SET status = 'done', verdict = %s, reason = %s, processed_at = %s
               WHERE id = %s""",
            (verdict, reason, now, row["id"]),
        )
    return True


def main():
    print("yaw-align worker started", flush=True)
    with connect() as conn:
        ensure_schema(conn)
        repaired = repair_half_states(conn)
        conn.execute(ADD_DONE_VERDICT_CONSTRAINT)
        conn.commit()
        if repaired:
            print(f"repaired {repaired} half-state logs", flush=True)
    while True:
        try:
            with connect() as conn:
                if claim_and_process(conn):
                    conn.commit()
                    time.sleep(POLL_SEC)
                else:
                    time.sleep(IDLE_SEC)
        except psycopg.Error as exc:
            print(f"worker db error: {exc}", flush=True)
            time.sleep(IDLE_SEC)


if __name__ == "__main__":
    main()
