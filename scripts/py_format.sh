#!/bin/bash
set -e

: <<'DOCSTRING'
This script formats Python code using the black formatter.
Usage: format.sh [--diff] [path1] [path2] ...
  --diff: Only check for formatting issues without making changes
  path:   Directory/directories to format (defaults to current directory)
DOCSTRING

# Default values
diff="false"
target_dirs=()

TARGET_PYTHON_VERSION="py312" # see: black --help (--target-version)

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --diff)
      diff="true"
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--diff] [path1] [path2] ..."
      echo "  --diff: Only check for formatting issues without making changes"
      echo "  path:   Directory/directories to format (defaults to current directory)"
      exit 0
      ;;
    *)
      # If it's not a flag, treat it as a target directory
      if [[ ! "$1" =~ ^-- ]]; then
        target_dirs+=("$1")
      else
        echo "Unknown option: $1"
        exit 1
      fi
      shift
      ;;
  esac
done

# Default to current directory if no paths provided
if [[ ${#target_dirs[@]} -eq 0 ]]; then
  target_dirs=(".")
fi

run_formatter_diff() {
  local target_dir="${1}"

  if [[ ! -d "${target_dir}" ]]; then
    echo "Error: Directory '${target_dir}' does not exist"
    return 1
  fi

  cd "${target_dir}"
  if ! uv run -- black --line-length=120 --diff --check --color --target-version="${TARGET_PYTHON_VERSION}" .; then
    echo "Formatting issues have been found in ${target_dir}, please run 'make format' to fix them."
    return 1
  fi
  echo "No formatting issues found in ${target_dir}."
  cd - > /dev/null
}

run_formatter_inplace() {
  local target_dir="${1}"

  if [[ ! -d "${target_dir}" ]]; then
    echo "Error: Directory '${target_dir}' does not exist"
    return 1
  fi

  echo "Formatting Python code in ${target_dir}..."
  cd "${target_dir}"
  uv run -- black --line-length=120 --target-version="${TARGET_PYTHON_VERSION}" .
  echo "Formatting completed for ${target_dir}."
  cd - > /dev/null
}


exit_code=0
for target_dir in "${target_dirs[@]}"; do
  if [ "${diff}" = "true" ]; then
    if ! run_formatter_diff "${target_dir}"; then
      exit_code=1
    fi
  else
    if ! run_formatter_inplace "${target_dir}"; then
      exit_code=1
    fi
  fi
done

exit "${exit_code}"
