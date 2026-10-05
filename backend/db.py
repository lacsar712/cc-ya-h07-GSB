import os

import psycopg
from psycopg.rows import dict_row

DSN = os.environ.get(
    "DATABASE_URL",
    "postgresql://app:app@localhost:54399/yawalign",
)


def connect():
    return psycopg.connect(DSN, row_factory=dict_row)


SCHEMA = """
CREATE TABLE IF NOT EXISTS yaw_logs (
    id serial PRIMARY KEY,
    turbine_code text NOT NULL,
    yaw_err_deg double precision NOT NULL,
    status text NOT NULL DEFAULT 'pending',
    verdict text,
    reason text,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL,
    processed_at timestamptz,
    CONSTRAINT yaw_logs_done_verdict_check
        CHECK (status <> 'done' OR verdict IN ('合格', '偏航超差'))
);
"""

# 旧表（约束建立前已存在）补同一道约束；须在半态数据修复之后执行。
ADD_DONE_VERDICT_CONSTRAINT = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'yaw_logs_done_verdict_check'
    ) THEN
        ALTER TABLE yaw_logs
            ADD CONSTRAINT yaw_logs_done_verdict_check
            CHECK (status <> 'done' OR verdict IN ('合格', '偏航超差'));
    END IF;
END$$;
"""
