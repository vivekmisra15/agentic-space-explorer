# test_supervisor.py
from supervisor import Supervisor

if __name__ == "__main__":
    sup = Supervisor(model="gemini-2.5-flash-lite")

    out = sup.run("Show me surprising trends in space missions over time.")

    print("\n--- State summary ---")
    print("raw_csv_path:", out.get("raw_csv_path"))
    print("enriched_csv_path:", out.get("enriched_csv_path"))

    assert out.get("raw_csv_path"), "raw_csv_path missing"
    assert out.get("enriched_csv_path"), "enriched_csv_path missing"
    
    print("\n--- Supervisor message ---")
    print(out["supervisor_message"])

    print("\n--- Logs ---")
    for entry in out["logs"]:
        print(entry)
