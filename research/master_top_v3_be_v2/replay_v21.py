"""Research-only Bubble Exhaustion V2.1 replay.
Input: extended_2026_mirror_monthly_lag25.csv in the same folder.
This does not reconstruct original publication vintages and is NOT OOS.
Usage: python replay_v21.py [input.csv] [output.csv]
"""
import csv
import math
import sys
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    arm_build: float = 85
    arm_memory: float = 80
    arm_cape: float = 85
    top_gate: float = 0.90
    arm_months: int = 2
    confirm_roll: float = 20
    off_roll: float = 10
    off_months: int = 2
    reset_build: float = 65
    reset_memory: float = 70
    reset_months: int = 3

def next_month(m):
    y, q = map(int, m.split("-"))
    assert 1 <= q <= 12
    return f"{y + (q == 12):04d}-{q % 12 + 1:02d}"

def val(r, k):
    try:
        n = float(r[k])
        return n if math.isfinite(n) else None
    except (KeyError, TypeError, ValueError):
        return None

def replay(rows, cfg=Config()):
    state = "IDLE"
    active = None
    events = []
    episode_id = 0
    arm_count = off_count = reset_count = 0
    previous = ""
    result = []
    for src in rows:
        row = dict(src)
        m = row["month"]
        if previous and m <= previous:
            raise ValueError("Dates not strictly increasing")
        gap = bool(previous and m != next_month(previous))
        previous = m
        build = val(row, "bubble_build")
        memory = val(row, "lev_memory")
        cape = val(row, "cape_pct")
        roll = val(row, "rollover")
        top = val(row, "top_ratio")
        complete = row.get("data_status") == "OK" and not gap
        complete = complete and all(x is not None for x in (build, memory, cape, roll, top))
        transition = ""
        if not complete:
            arm_count = off_count = reset_count = 0
            reported = "PROVISIONAL" if row.get("data_status") == "PROVISIONAL_MONTH" else "UNVERIFIED_DATA"
        else:
            arm = build >= cfg.arm_build and memory >= cfg.arm_memory and cape >= cfg.arm_cape and top >= cfg.top_gate
            confirm = roll >= cfg.confirm_roll and top >= cfg.top_gate
            off = roll <= cfg.off_roll
            reset = build <= cfg.reset_build and memory <= cfg.reset_memory
            if state == "IDLE":
                arm_count = arm_count + 1 if arm else 0
                if arm_count >= cfg.arm_months:
                    episode_id += 1
                    active = {"id": episode_id, "confirmed": False}
                    state = "ARMED"
                    transition = "ARM"
                    arm_count = 0
            else:
                if state != "ROLLOVER_ACTIVE" and confirm:
                    transition = "RECONFIRM" if active["confirmed"] else "CONFIRM"
                    active["confirmed"] = True
                    state = "ROLLOVER_ACTIVE"
                    off_count = 0
                elif state == "ROLLOVER_ACTIVE":
                    off_count = off_count + 1 if off else 0
                    if off_count >= cfg.off_months:
                        state = "ARMED_REHEATED"
                        transition = "REHEAT_DOWNGRADE"
                        off_count = 0
                reset_count = reset_count + 1 if reset else 0
                if reset_count >= cfg.reset_months:
                    state = "IDLE"
                    transition = "RESET"
                    reset_count = off_count = arm_count = 0
            reported = state
        if transition:
            events.append({"month": m, "event": transition, "episode_id": active["id"] if active else episode_id})
            if transition == "RESET":
                active = None
        row.update({
            "state_v21": reported,
            "episode_id_v21": active["id"] if active else "",
            "ever_confirmed_in_episode": bool(active and active["confirmed"]),
            "current_confirmation": bool(complete and state == "ROLLOVER_ACTIVE"),
            "transition_v21": transition
        })
        result.append(row)
    return result, events

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "extended_2026_mirror_monthly_lag25.csv"
    dst = sys.argv[2] if len(sys.argv) > 2 else "monthly_states_v21_replayed.csv"
    with open(src, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    out, events = replay(rows)
    with open(dst, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0]))
        writer.writeheader()
        writer.writerows(out)
    print("Research only: ", len(out), "scored rows and", len(events), "transitions")
    print("Recent events:", events[-5:])

if __name__ == "__main__":
    main()
