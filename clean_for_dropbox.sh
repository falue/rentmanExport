#!/bin/bash

# Check if a folder path was provided
if [ -z "$1" ]; then
  echo "Usage: $0 <root_folder>"
  exit 1
fi

ROOT_FOLDER="$1"

# Check if the root folder exists
if [ ! -d "$ROOT_FOLDER" ]; then
  echo "Error: Folder '$ROOT_FOLDER' does not exist."
  exit 1
fi

# List of extensions to keep (add more extensions here)
EXTENSIONS=("pdf" "jpg" "png")

# Build the find command with the allowed extensions
FIND_CMD="find \"$ROOT_FOLDER\" -type f"
for ext in "${EXTENSIONS[@]}"; do
  FIND_CMD+=" ! -name \"*.$ext\""
done

# Add the action to delete files
FIND_CMD+=" -exec rm {} +"

# Execute the command safely
echo "Deleting files that do not match extensions: ${EXTENSIONS[*]}"
eval "$FIND_CMD"

echo "Cleanup complete."


# Use like this
# ./clean_for_dropbox.sh ./_archive/equipmentDump_dropbox