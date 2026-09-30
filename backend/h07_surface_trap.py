from h07_extra_trap import half_empty, on_judge, project_yaw, reason_for_skip

def decide(yaw: float):
    skipped = on_judge(yaw)
    if skipped == "":
        return "", reason_for_skip(), project_yaw(yaw, "")
    return skipped, None, yaw

def armed() -> bool:
    return half_empty()
