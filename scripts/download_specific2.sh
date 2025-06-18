#!/bin/bash

# Check if at least one folder name is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <folder1> [folder2] [folder3] ..."
    echo "Provide one or more folder names to download."
    exit 1
fi

# Variables
REMOTE_PATH="shimizudbx:/DATA/CocoTransport"
LOCAL_DEST="/mnt/sun-temp/TEMP/MOCK_ARETHA_VIDEO/"

# Ensure local destination directory exists
mkdir -p "$LOCAL_DEST"
echo "Removing files and directories older than 2 days in $LOCAL_DEST..."
find "$LOCAL_DEST" -mindepth 1 -ctime +2 -exec rm -rf {} +

# Loop through provided folder names
for SELECTED_FOLDER in "$@"; do
    echo "Processing folder: $SELECTED_FOLDER"

    # Check if folder exists in remote
    if ! rclone lsd "$REMOTE_PATH" | awk '{print $NF}' | grep -qx "$SELECTED_FOLDER"; then
        echo "Error: Folder '$SELECTED_FOLDER' not found in remote. Skipping..."
        continue
    fi

    # Create a unique destination name
    UNIQUE_ID=$(date +%s%N)
    DEST_FOLDER="${LOCAL_DEST}/${SELECTED_FOLDER}_${UNIQUE_ID}"

    # Download directly to the unique local folder
    echo "Downloading to $DEST_FOLDER..."
    rclone copy "$REMOTE_PATH/$SELECTED_FOLDER" "$DEST_FOLDER"

    if [ $? -eq 0 ]; then
        echo "Successfully downloaded: $SELECTED_FOLDER to $DEST_FOLDER"
    else
        echo "Error downloading: $SELECTED_FOLDER"
        rm -rf "$DEST_FOLDER"  # Clean up in case of error
        continue
    fi
done

echo "All specified folders processed."
