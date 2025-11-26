#!/bin/bash

# Usage: ./process_repos.sh [language]
# language: go, java, kotlin, python, javascript, typescript (default: go)

LANGUAGE="${1:-go}"

# Set CSV file and clone directory based on language
case "$LANGUAGE" in
    go|golang)
        CSV_FILE="data/data/golang_repos.csv"
        CLONE_DIR="sample/go"
        ;;
    java)
        CSV_FILE="data/data/java_repos.csv"
        CLONE_DIR="sample/java"
        ;;
    kotlin)
        CSV_FILE="data/data/kotlin_repos.csv"
        CLONE_DIR="sample/kotlin"
        ;;
    python)
        CSV_FILE="data/data/python_repos.csv"
        CLONE_DIR="sample/python"
        ;;
    javascript|js)
        CSV_FILE="data/data/javascript_repos.csv"
        CLONE_DIR="sample/javascript"
        ;;
    typescript|ts)
        CSV_FILE="data/data/typescript_repos.csv"
        CLONE_DIR="sample/typescript"
        ;;
    *)
        echo "Unknown language: $LANGUAGE"
        echo "Supported languages: go, java, kotlin, python, javascript, typescript"
        exit 1
        ;;
esac

# Directory to store results
RESULTS_DIR="results/$LANGUAGE"

# Ensure the clone and results directories exist
mkdir -p "$CLONE_DIR"
mkdir -p "$RESULTS_DIR"

echo "Processing $LANGUAGE repositories from $CSV_FILE"
echo "Cloning to: $CLONE_DIR"
echo "Results in: $RESULTS_DIR"
echo "---"

# Read the CSV file line by line, skipping the header
while IFS=, read -r name full_name language stars forks size url; do
    # Skip the header line
    if [ "$name" == "name" ]; then
        continue
    fi

    # Extract the repository name
    REPO_NAME=$(basename "$full_name")

    # Clone the repository
    REPO_PATH="$CLONE_DIR/$REPO_NAME"
    if [ ! -d "$REPO_PATH" ]; then
        echo "Cloning $url into $REPO_PATH..."
        git clone --depth 1 "$url" "$REPO_PATH" 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "Failed to clone $url. Skipping..."
            continue
        fi
    else
        echo "Repository $REPO_NAME already cloned. Skipping..."
    fi

    # Run larek debug and save the result
    OUTPUT_FILE="$RESULTS_DIR/$REPO_NAME.build.yaml"
    echo "Running larek debug on $REPO_PATH..."
    larek debug "$REPO_PATH" > "$OUTPUT_FILE" 2>&1

    echo "Saved result to $OUTPUT_FILE"
done < "$CSV_FILE"

echo "---"
echo "Done processing $LANGUAGE repositories"