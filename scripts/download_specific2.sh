#!/bin/bash

# Check if at least one folder name is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <folder1> [folder2] [folder3] ..."
    exit 1
fi

# Variables
REMOTE_PATH="shimizudbx:/DATA/CocoTransport"
LOCAL_DEST="/mnt/sun-temp/TEMP/MOCK_ARETHA/"
TEMP_DIR="/mnt/sun-temp/TEMP/rclone_temp"

# Ensure local destination directories exist
mkdir -p "$LOCAL_DEST" "$TEMP_DIR"

# Cleanup old files
#echo "Removing files and directories older than 2 days in $LOCAL_DEST..."
#find "$LOCAL_DEST" -mindepth 1 -ctime +2 -exec rm -rf {} +

# Loop through each selected folder
for SELECTED_FOLDER in "$@"; do
    echo "Processing folder: $SELECTED_FOLDER"

    # Check if folder exists in remote
    if ! rclone lsd "$REMOTE_PATH" | awk '{print $NF}' | grep -qx "$SELECTED_FOLDER"; then
        echo "Error: Folder '$SELECTED_FOLDER' not found in remote. Skipping..."
        continue
    fi

    # Clean temp directory
    rm -rf "$TEMP_DIR"/*

    # rclone copy to temp directory
    echo "Downloading $SELECTED_FOLDER to temporary location..."
    rclone copy "$REMOTE_PATH/$SELECTED_FOLDER" "$TEMP_DIR"

    if [ $? -ne 0 ]; then
        echo "Error downloading: $SELECTED_FOLDER"
        continue
    fi

    # Move each top-level subfolder to LOCAL_DEST and rename with unique timestamp
    for SUBFOLDER in "$TEMP_DIR"/*; do
        if [ -d "$SUBFOLDER" ]; then
            TIMESTAMP=$(date +%d_%H%M%S%3N)
            DEST_FOLDER="$LOCAL_DEST/$TIMESTAMP"
            mv "$SUBFOLDER" "$DEST_FOLDER"
            echo "Moved $(basename "$SUBFOLDER") to $DEST_FOLDER"
        fi
    done
done

echo "All specified folders processed."
