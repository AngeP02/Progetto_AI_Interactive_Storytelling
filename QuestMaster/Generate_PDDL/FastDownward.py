import os
import re
import requests
from pathlib import Path
import subprocess

# ========== VALIDAZIONE ==========
def validate_with_fastdownward(domain_path, problem_path):
    fast_downward_path = r"C:\Users\ANGELICA\Desktop\SOFTWARE\FASTDOWNWARD\fast-downward-24.06.1\fast-downward.py"
    if not os.path.exists(fast_downward_path):
        print("⚠️ Fast Downward not found")
        return False

    cmd = ["python", fast_downward_path, str(domain_path), str(problem_path),
           "--search", "astar(lmcut())"]

    try:
        print("▶️ Running Fast Downward...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        print(result.stdout)
        if "Solution found!" in result.stdout or result.returncode == 0:
            print("✅ PROBLEM IS SOLVABLE!")
            plan_match = re.search(r"Plan length: (\d+)", result.stdout)
            if plan_match:
                print(f"   📊 Plan length: {plan_match.group(1)} steps")
            return True
        else:
            print("❌ No solution found")
            if "dead end" in result.stdout.lower():
                print("   Issue: Initial state unreachable")
            return False

    except subprocess.TimeoutExpired:
        print("⏱️ Timeout (problem too complex)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


# ========== MAIN ==========
if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent

    try:

        OUTPUT_DIR = Path("Generated_PDDL/pddl_output")
        problem_path = OUTPUT_DIR / "problem.pddl"
        domain_path = OUTPUT_DIR / "domain.pddl"
        print("Generating PDDL...")
        print(problem_path)
        print(domain_path)

        if domain_path and problem_path:
            print("\n" + "=" * 60)
            validate_with_fastdownward(domain_path, problem_path)
        else:
            print("❌ Failed to generate PDDL")


    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()