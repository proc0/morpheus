#!/bin/bash

# 1. Check if the user forgot to provide the argument
if [ -z "$1" ]; then
    echo "Error: No directory path provided."
    echo "Usage: $0 /path/to/directory"
    exit 1
fi

# 2. Assign the argument to a clear variable name
target_dir="$1"

# 3. Check if the provided path actually exists and is a directory
if [ ! -d "$target_dir" ]; then
    echo "Error: '$target_dir' is not a valid directory."
    exit 1
fi

# 4. Now safely use the directory to list files
echo "Listing files in: $target_dir"
for file in "$target_dir"/*; do
    if [ -f "$file" ]; then
        basename "$file"
    fi
done