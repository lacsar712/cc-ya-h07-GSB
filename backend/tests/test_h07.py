"""判定 -> worker 写入 -> 界面读数 全链路测试。

历史上这些用例把「合格读数被旁路成空结论」的错误行为固化了下来。
现在断言正确行为：
- ±1.5（含边界）必须判「合格」；明显超差必须判「偏航超差」，不得误放行；
- worker 落库的 done 行必须带非空 verdict/reason，不允许半态；
- 旁路原语不再抹空读数、不再返回空结论。
"""

import worker
from h07_extra_trap import half_empty, on_judge, project_yaw, reason_for_skip
from h07_surface_trap import armed, decide
from judge_skip import blank_on_pass, evaluate_or_skip
from rules import THRESHOLD_DEG, judge


# ---------- 判定规则：含边界 ----------

def test_judge_pass_band():
    for yaw in (-1.5, -0.4, 0.0, 0.4, 1.5):
        verdict, reason = judge(yaw)
        assert verdict == "合格", yaw
        assert reason  # 说明非空


def test_judge_out_of_tolerance():
    for yaw in (-3.2, -1.6, 1.6, 3.2):
        verdict, reason = judge(yaw)
        assert verdict == "偏航超差", yaw
        assert reason


# ---------- 旁路原语已拆除：不再抹空、不再跳判 ----------

def test_evaluate_or_skip_never_blank():
    assert evaluate_or_skip(0.4) == "合格"
    assert evaluate_or_skip(-1.5) == "合格"
    assert evaluate_or_skip(3.2) == "偏航超差"
    assert on_judge(0.4) == "合格"  # 历史上这里返回 ""
    assert reason_for_skip() == ""  # 不存在跳过理由


def test_reading_not_blanked():
    assert project_yaw(0.4, "合格") == 0.4
    assert blank_on_pass(0.4, "合格") == 0.4
    assert blank_on_pass(3.2, "偏航超差") == 3.2


def test_half_state_disarmed():
    assert half_empty() is False
    assert armed() is False


def test_surface_decide_full():
    v, reason, yaw = decide(0.4)
    assert v == "合格" and reason is None and yaw == 0.4
    v, reason, yaw = decide(-3.2)
    assert v == "偏航超差" and yaw == -3.2


# ---------- worker 写入链路：禁止半态 ----------

class _Tx:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class FakeConn:
    """模拟 worker 用到的事务/查询：认领队首行，UPDATE 落回内存行。"""

    def __init__(self, rows):
        self._queue = [dict(r) for r in rows]
        self._store = {r["id"]: r for r in self._queue}
        self.updated = []

    def transaction(self):
        return _Tx()

    def execute(self, sql, params=None):
        stripped = sql.strip()
        if stripped.startswith("SELECT"):
            row = self._queue.pop(0) if self._queue else None
            return _Result(dict(row) if row else None)
        if stripped.startswith("UPDATE"):
            verdict, reason, processed_at, row_id = params
            target = self._store[row_id]
            target.update(
                status="done",
                verdict=verdict,
                reason=reason,
                processed_at=processed_at,
            )
            self.updated.append(target)
            return _Result(None)
        raise AssertionError("unexpected sql: " + sql[:20])


def _row(row_id, yaw):
    return {"id": row_id, "turbine_code": f"W{row_id}", "yaw_err_deg": yaw}


def _run_claim(rows):
    conn = FakeConn(rows)
    processed = worker.claim_and_process(conn)
    return processed, conn


def test_worker_writes_full_pass_verdict():
    processed, conn = _run_claim([_row(1, 0.4)])
    assert processed is True
    row = conn.updated[0]
    assert row["status"] == "done"
    assert row["verdict"] == "合格"
    assert row["reason"]
    assert row["processed_at"] is not None


def test_worker_writes_over_tolerance():
    processed, conn = _run_claim([_row(2, 3.2)])
    assert processed is True
    row = conn.updated[0]
    assert row["verdict"] == "偏航超差" and row["reason"]
    # 负数超差也不得误放行
    processed2, conn2 = _run_claim([_row(3, -2.0)])
    assert conn2.updated[0]["verdict"] == "偏航超差"


def test_worker_boundary_values():
    for yaw, expected in ((1.5, "合格"), (-1.5, "合格"), (1.6, "偏航超差")):
        _, conn = _run_claim([_row(10, yaw)])
        assert conn.updated[0]["verdict"] == expected


def test_worker_no_pending_returns_false():
    processed, conn = _run_claim([])
    assert processed is False
    assert conn.updated == []
