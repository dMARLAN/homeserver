#!/bin/bash
set -e

: <<'DOCSTRING'
This script formats Python code using the black formatter.
Usage: format.sh [--diff] [path]
  --diff: Only check for formatting issues without making changes
  path:   Directory to format (defaults to current directory)
DOCSTRING

# Default values
diff="false"
target_dir="."

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --diff)
      diff="true"
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--diff] [path]"
      echo "  --diff: Only check for formatting issues without making changes"
      echo "  path:   Directory to format (defaults to current directory)"
      exit 0
      ;;
    *)
      # If it's not a flag, treat it as the target directory
      if [[ ! "$1" =~ ^-- ]]; then
        target_dir="$1"
      else
        echo "Unknown option: $1"
        exit 1
      fi
      shift
      ;;
  esac
done

# Validate target directory exists
if [[ ! -d "${target_dir}" ]]; then
  echo "Error: Directory '${target_dir}' does not exist"
  exit 1
fi

cd "${target_dir}"

TARGET_PYTHON_VERSION="py312" # see: black --help (--target-version)

run_formatter_diff() {
  if ! uv run -- black --line-length=120 --diff --check --color --target-version="${TARGET_PYTHON_VERSION}" .; then
    echo "Formatting issues have been found in ${target_dir}, please run 'make format' to fix them."
    exit 1
  fi
  echo "No formatting issues found in ${target_dir}."
}

run_formatter_inplace() {
  echo "Formatting Python code in ${target_dir}..."
  uv run -- black --line-length=120 --target-version="${TARGET_PYTHON_VERSION}" .
  echo "Formatting completed for ${target_dir}."
}

if [ "${diff}" = "true" ]; then
  run_formatter_diff
else
  run_formatter_inplace
fi
