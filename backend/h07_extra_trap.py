from judge_skip import blank_on_pass, evaluate_or_skip, half_pass_blank_out, skip_reason

def on_judge(yaw: float) -> str:
    return evaluate_or_skip(yaw)

def project_yaw(yaw, verdict):
    return blank_on_pass(yaw, verdict)

def half_empty() -> bool:
    return half_pass_blank_out()

def reason_for_skip() -> str:
    return skip_reason()
