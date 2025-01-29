#!/bin/bash

# To set up rclone, follow instructions at https://rclone.org/dropbox/

# Check if at least one folder name is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <folder1> [folder2] [folder3] ..."
    echo "Provide one or more folder names to download."
    exit 1
fi

# Variables
REMOTE_PATH="shimizudbx:/DATA/PRINCE" # Replace with your rclone path
LOCAL_DEST="/mnt/sun-temp/TEMP/MOCK_ARETHA2/"

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

    # Download the selected folder and manually flatten the structure
    echo "Downloading and flattening folder: $SELECTED_FOLDER"
    TEMP_DIR="/mnt/sun-temp/TEMP/temp2/"  # Temporary directory for intermediate download

    # Copy the folder into the temporary directory
    rclone copy "$REMOTE_PATH/$SELECTED_FOLDER" "$TEMP_DIR" --progress

    if [ $? -eq 0 ]; then
        echo "Successfully downloaded: $SELECTED_FOLDER"

        # Move files and subdirectories from TEMP_DIR to LOCAL_DEST (flattening the structure)
        find "$TEMP_DIR" -mindepth 1 -maxdepth 1 -exec mv -t "$LOCAL_DEST" {} +

        # Clean up the temporary directory
        rm -rf "$TEMP_DIR"
    else
        echo "Error downloading: $SELECTED_FOLDER"
        rm -rf "$TEMP_DIR"  # Clean up in case of error
        continue
    fi

    # Unzip files and maintain the correct structure
    echo "Checking for zipped files in $LOCAL_DEST..."
    find "$LOCAL_DEST" -type f -name "*.zip" | while read -r zip_file; do
      # Get the directory containing the .zip file
      parent_dir=$(dirname "$zip_file")

      # Get the base name of the .zip file (without extension)
      folder_name=$(basename "$zip_file" .zip)

      # Create the extraction directory
      extract_dir="$parent_dir/$folder_name"
      mkdir -p "$extract_dir"

      # Extract the .zip file into the corresponding folder
      unzip -q "$zip_file" -d "$extract_dir"
      rm "$zip_file"
      echo "Extracted $zip_file to $extract_dir"
    done

    echo "Folder $SELECTED_FOLDER processed with flattened structure!"
done

echo "All specified folders processed."
