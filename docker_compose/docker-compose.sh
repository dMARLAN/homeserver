#!/bin/bash

parse_args() {
    INCLUDE_PATTERNS=()
    EXCLUDE_PATTERNS=()
    COMPOSE_COMMAND=()
    while (( "$#" )); do
        case "$1" in
            --include=*)
                value="${1#*=}"
                IFS=',' read -ra arr <<< "$value"
                for pattern in "${arr[@]}"; do
                    INCLUDE_PATTERNS+=("$pattern")
                done
                ;;
            --include)
                shift
                [ -z "$1" ] && { echo "Missing argument for --include"; exit 1; }
                value="$1"
                IFS=',' read -ra arr <<< "$value"
                for pattern in "${arr[@]}"; do
                    INCLUDE_PATTERNS+=("$pattern")
                done
                ;;
            --exclude=*)
                value="${1#*=}"
                IFS=',' read -ra arr <<< "$value"
                for pattern in "${arr[@]}"; do
                    EXCLUDE_PATTERNS+=("$pattern")
                done
                ;;
            --exclude)
                shift
                [ -z "$1" ] && { echo "Missing argument for --exclude"; exit 1; }
                value="$1"
                IFS=',' read -ra arr <<< "$value"
                for pattern in "${arr[@]}"; do
                    EXCLUDE_PATTERNS+=("$pattern")
                done
                ;;
            -h|--help)
                print_help
                exit 0
                ;;
            --)
                shift
                COMPOSE_COMMAND=("$@")
                break
                ;;
            *)
                COMPOSE_COMMAND+=("$1")
                ;;
        esac
        shift
    done

    [ "${#COMPOSE_COMMAND[@]}" -eq 0 ] && COMPOSE_COMMAND=("up" "-d")
}

get_default_files() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    find "${script_dir}" -type f \( -name "*.yml" -o -name "*.yaml" \) \
         -not -path "*/\.*" \
         -not -path "*/config/*" \
         -not -path "*/default_excluded/*"
}

apply_inclusions() {
    local pattern=$1
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    find "${script_dir}/default_excluded" -type f \( -name "*.yml" -o -name "*.yaml" \) -iname "${pattern}"
}

apply_exclusions() {
    local input_files=("$@")
    local result=()
    for file in "${input_files[@]}"; do
        local exclude=false
        for pattern in "${EXCLUDE_PATTERNS[@]}"; do
            if [[ "${file}" == *"${pattern}"* ]]; then
                exclude=true
                break
            fi
        done
        if ! $exclude; then
            result+=("${file}")
        fi
    done
    for file in "${result[@]}"; do
        echo "${file}"
    done
}

find_compose_files() {
    local files=()

    # Get default files.
    while IFS= read -r line; do
        files+=("${line}")
    done < <(get_default_files)

    # If include patterns are provided, add those files.
    if [ "${#INCLUDE_PATTERNS[@]}" -gt 0 ]; then
        for pattern in "${INCLUDE_PATTERNS[@]}"; do
            while IFS= read -r line; do
                files+=("${line}")
            done < <(apply_inclusions "${pattern}")
        done
    fi

    # Apply exclusion filters if provided.
    if [ "${#EXCLUDE_PATTERNS[@]}" -gt 0 ]; then
        local temp_files=("${files[@]}")
        files=()
        while IFS= read -r file; do
            files+=("${file}")
        done < <(apply_exclusions "${temp_files[@]}")
    fi

    # Output the final list of files.
    for file in "${files[@]}"; do
        echo "${file}"
    done
}

build_compose_command() {
    local cmd=("docker" "compose")
    for file in "${@}"; do
        cmd+=("-f" "${file}")
    done

    cmd+=( "${COMPOSE_COMMAND[@]}" )
    for arg in "${cmd[@]}"; do
        printf "%s\n" "${arg}"
    done
}

print_help() {
    echo "Usage: ${0} [--include pattern] [--exclude pattern] [--] [COMMAND]"
    echo
    echo "Discovers Docker Compose files and runs docker compose with the specified command."
    echo "By default, files in the default_excluded folder are ignored."
    echo "If --include is provided, files in default_excluded matching the pattern are added."
    echo "If --exclude is provided, files matching the pattern (as a substring) are removed from the list."
    echo "Using both --include and --exclude is not allowed."
    echo
    echo "Examples:"
    echo "  ${0}                           # Runs 'docker compose up -d' with all default files"
    echo "  ${0} --include compose.restore-db.yaml -- build  # Adds 'compose.restore-db.yaml' from default_excluded"
    echo "  ${0} --exclude compose.api.yaml down   # Excludes any file containing 'compose.api.yaml' and runs 'docker compose down'"
}

main() {
    parse_args "${@}"
    echo "🔍 Discovering Docker Compose files in scripts directory..."

    # Read the list of files into an array.
    files_array=()
    while IFS= read -r line; do
        files_array+=("${line}")
    done < <(find_compose_files)

    if [ "${#files_array[@]}" -eq 0 ]; then
        echo "❌ No Docker Compose files found in scripts directory!"
        exit 1
    fi

    echo "📄 Found the following Docker Compose files:"
    for file in "${files_array[@]}"; do
        echo "  - ${file}"
    done

    echo
    echo "🐋 Running Docker Compose..."
    cmd=()
    while IFS= read -r line; do
        cmd+=("${line}")
    done < <(build_compose_command "${files_array[@]}")
    echo "Executing:" "${cmd[@]}"
    echo

    exec "${cmd[@]}"
}

main "${@}"
