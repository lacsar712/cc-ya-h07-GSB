"""判定 -> 写入 链路测试：够线必须落「合格」，超差必须判「偏航超差」，不允许半态。"""

import worker
from rules import judge


def test_judge_boundaries():
    assert judge(0.4)[0] == "合格"
    assert judge(-1.5)[0] == "合格"
    assert judge(1.5)[0] == "合格"
    assert judge(-1.49)[0] == "合格"
    assert judge(3.2)[0] == "偏航超差"
    assert judge(-3.2)[0] == "偏航超差"
    assert judge(1.51)[0] == "偏航超差"


class FakeCursor:
    def __init__(self, conn, result=None):
        self.conn = conn
        self.result = result

    def fetchone(self):
        return self.result

    def fetchall(self):
        return self.result


class FakeConn:
    """记录 UPDATE 写入内容的最小假连接。"""

    def __init__(self, claimed_row):
        self.claimed_row = claimed_row
        self.updates = []

    def transaction(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        if normalized.startswith("SELECT"):
            return FakeCursor(self, self.claimed_row)
        if normalized.startswith("UPDATE"):
            self.updates.append(params)
        return FakeCursor(self)


def _claim_params(conn):
    assert len(conn.updates) == 1
    verdict, reason, processed_at, row_id = conn.updates[0]
    return verdict, reason, row_id


def test_claim_writes_pass_verdict_in_range():
    conn = FakeConn({"id": 7, "turbine_code": "W07", "yaw_err_deg": 0.4})
    assert worker.claim_and_process(conn) is True
    verdict, reason, row_id = _claim_params(conn)
    assert verdict == "合格"
    assert reason
    assert row_id == 7


def test_claim_writes_fail_verdict_out_of_range():
    conn = FakeConn({"id": 8, "turbine_code": "W08", "yaw_err_deg": 3.2})
    assert worker.claim_and_process(conn) is True
    verdict, reason, row_id = _claim_params(conn)
    assert verdict == "偏航超差"
    assert reason
    assert row_id == 8


def test_claim_negative_in_range_is_pass():
    conn = FakeConn({"id": 9, "turbine_code": "W09", "yaw_err_deg": -1.5})
    worker.claim_and_process(conn)
    verdict, _, _ = _claim_params(conn)
    assert verdict == "合格"


def test_claim_no_pending_returns_false():
    conn = FakeConn(None)
    assert worker.claim_and_process(conn) is False
    assert conn.updates == []


class FakeRepairConn:
    def __init__(self, rows):
        self.rows = rows
        self.updates = []

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        if normalized.startswith("SELECT"):
            return FakeCursor(self, self.rows)
        if normalized.startswith("UPDATE"):
            self.updates.append(params)
        return FakeCursor(self)


def test_repair_half_states_fills_missing_verdict():
    conn = FakeRepairConn(
        [
            {"id": 1, "yaw_err_deg": 0.4},
            {"id": 2, "yaw_err_deg": 3.2},
        ]
    )
    fixed = worker.repair_half_states(conn)
    assert fixed == 2
    by_id = {u[3]: u[0] for u in conn.updates}
    assert by_id == {1: "合格", 2: "偏航超差"}
