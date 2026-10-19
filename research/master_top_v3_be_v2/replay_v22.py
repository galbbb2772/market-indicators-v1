"""Research-only V2.2 wrapper around V2.1 immutable lifecycle and evidence gates.
No score is declared actual publication-vintage PIT; input file is a proxy.
python replay_v22.py [monthly_proxy.csv] [output.csv]
"""
import csv
import sys
from replay_v21 import Config, replay
def research_replay(rows, cfg=Config()):
    states, events = replay(rows, cfg)
    for row in states:
        valid = (row.get("data_status") == "OK"
                 and row["state_v21"] not in ("PROVISIONAL", "UNVERIFIED_DATA"))
        row["v22_verified_month"] = bool(valid)
        row["v22_display_state"] = row["state_v21"] if valid else "UNVERIFIED_DATA"
        row["v22_active_confirmation"] = bool(valid and row["current_confirmation"])
        row["v22_publication_vintage_verified"] = False
        row["v22_research_status"] = "HISTORICAL_REVISED_MIRROR_AND_LAG_ASSUMPTION"
    return states, events

def main():
    src = sys.argv[1] if len(sys.argv)>1 else "extended_2026_mirror_monthly_lag25.csv"
    dst = sys.argv[2] if len(sys.argv)>2 else "monthly_states_v22_replayed.csv"
    with open(src, newline="", encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    state, events = research_replay(rows)
    with open(dst, "w", newline="", encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(state[0]))
        writer.writeheader()
        writer.writerows(state)
    print(f"V2.2 research-only: {len(state)} rows; {len(events)} transitions; no OOS/PIT certification.")
if __name__ == "__main__":
    main()
