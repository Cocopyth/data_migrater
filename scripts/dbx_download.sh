#!/bin/bash

#To set up rclone folloz instructions at https://rclone.org/dropbox/
# Variables
REMOTE_PATH="shimizudbx:/DATA/PRINCE" # Replace with your rclone path
LOCAL_DEST="/media/admincorentin/5644166e-8493-472e-9f2e-a710ced69b0b/dbx_copy" # Replace with your local destination directory

# Ensure local destination directory exists
mkdir -p "$LOCAL_DEST"

# List folders, sort by name, and select the first two
FOLDERS=$(rclone lsd "$REMOTE_PATH" | awk '{print $NF}' | sort | head -n 3)

# Download the selected folders
for FOLDER in $FOLDERS; do
    echo "Downloading folder: $FOLDER"
    rclone copy "$REMOTE_PATH/$FOLDER" "$LOCAL_DEST/$FOLDER" --progress
    if [ $? -eq 0 ]; then
        echo "Successfully downloaded: $FOLDER"
        echo "Checking for zipped files in $LOCAL_DEST/$FOLDER..."
        find "$LOCAL_DEST/$FOLDER" -type f -name "*.zip" | while read -r ZIPFILE; do
            UNZIP_DIR="$(dirname "$ZIPFILE")/$(basename "$ZIPFILE" .zip)"
            mkdir -p "$UNZIP_DIR"
            echo "Unzipping: $ZIPFILE to $UNZIP_DIR"
            unzip -o "$ZIPFILE" -d "$UNZIP_DIR" && rm "$ZIPFILE"
        done
    else
        echo "Error downloading: $FOLDER"
    fi
done

echo "First 2 folders processed!"
