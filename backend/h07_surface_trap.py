from rules import judge
from h07_extra_trap import half_empty


def decide(yaw: float):
    """直通判定：返回 (结论, None, 原读数)，读数不抹空。"""
    verdict, _reason = judge(float(yaw))
    return verdict, None, float(yaw)


def armed() -> bool:
    """半态旁路是否仍布防：已拆除，恒为 False。"""
    return half_empty()
