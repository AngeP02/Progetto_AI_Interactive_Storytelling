import subprocess

domain = "pddl_files/domain.pddl"
problem = "pddl_files/problem.pddl"

subprocess.run([
    "python",
    "C:\\Users\\ANGELICA\\Desktop\\SOFTWARE\\FASTDOWNWARD\\fast-downward-24.06.1\\fast-downward.py",
    domain,
    problem,
    "--search", "astar(lmcut())"
])
