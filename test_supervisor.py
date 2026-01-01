# test_supervisor.py
from supervisor import Supervisor
import os   

if __name__ == "__main__":
    sup = Supervisor(model="gemini-2.5-flash-lite")

    out = sup.run("Show me the most interesting insights from 1975 to 1990.")

    print("\n--- Analysis artifacts ---")
    print("analysis_plan_path:", out.get("analysis_plan_path"))
    print("analysis_md_path:", out.get("analysis_md_path"))
    print("plot_paths:", out.get("plot_paths"))

    assert out.get("analysis_plan_path"), "analysis_plan_path missing"
    assert out.get("analysis_md_path"), "analysis_md_path missing"
    assert out.get("plot_paths") and len(out["plot_paths"]) > 0, "plot_paths missing/empty"

    print("\n--- Eval artifacts ---")
    print("eval_md_path:", out.get("eval_md_path"))
    print("eval_json_path:", out.get("eval_json_path"))
    print("eval_pass:", out.get("eval_pass"))

    # EvalAgent assertions
    assert out.get("eval_md_path"), "eval_md_path missing"
    assert out.get("eval_json_path"), "eval_json_path missing"
    assert out.get("eval_pass") in (True, False), "eval_pass missing or invalid"

    assert os.path.exists(out["eval_md_path"]), "eval.md file does not exist"
    assert os.path.exists(out["eval_json_path"]), "eval JSON file does not exist"


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
