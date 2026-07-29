import subprocess
import sys


def main():
    # Search for TODO comments in staged Python files
    # Command to get list of staged files that are added or modified
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"]
    staged_files = subprocess.run(
        cmd, capture_output=True, text=True, check=False
    ).stdout.split()

    # Filter for Python files
    python_files = [
        f
        for f in staged_files
        if f.endswith(".py") and f != "scripts/pre-commit/check_remove_comments.py"
    ]

    # Run git grep on these Python files if any
    if python_files:
        grep_cmd = ["git", "grep", "--cached", "-n", "# RMPC", "--"] + python_files
        result = subprocess.run(grep_cmd, capture_output=True, text=True, check=False)

        if result.stdout:
            print("Commit failed: RMPC comments found in the following files:")
            print(result.stdout)
            sys.exit(1)
        else:
            sys.exit(0)
    else:
        print("No Python files to check.")


if __name__ == "__main__":
    main()
