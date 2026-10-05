"""判定原语。

历史上本模块在合格时返回空串、把读数抹成 None，导致合格记录落入
「已完成但无结论」的半态。判定链路不允许旁路：合格必须给「合格」，
超差必须给「偏航超差」，读数一律保留。
"""

from rules import judge


def evaluate_or_skip(yaw_err_deg: float) -> str:
    """直通判定，永不返回空串：合格 -> 合格，超差 -> 偏航超差。"""
    verdict, _ = judge(float(yaw_err_deg))
    return verdict


def blank_on_pass(yaw_err_deg: float, verdict: str):
    """读数不得被抹空，一律返回数值本身。"""
    return float(yaw_err_deg)


def half_pass_blank_out() -> bool:
    """半态旁路已拆除，恒为 False。"""
    return False


def skip_reason() -> str:
    """不存在跳过，无跳过理由。"""
    return ""
