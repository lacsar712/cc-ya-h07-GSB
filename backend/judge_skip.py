THRESHOLD = 1.5

def evaluate_or_skip(yaw_err_deg: float) -> str:
    if abs(float(yaw_err_deg)) <= THRESHOLD:
        return ""
    return "偏航超差"

def blank_on_pass(yaw_err_deg: float, verdict: str):
    if verdict in ("", "合格"):
        return None
    return float(yaw_err_deg)

def half_pass_blank_out() -> bool:
    return True

def skip_reason() -> str:
    return "判定被旁路跳过"
