# test_supervisor.py
from supervisor import Supervisor

if __name__ == "__main__":
    sup = Supervisor(model="gemini-2.5-flash-lite")

    out = sup.run("Show me surprising trends in space missions over time.")

    print("\n--- Supervisor message ---")
    print(out["supervisor_message"])

    print("\n--- Logs ---")
    for entry in out["logs"]:
        print(entry)
