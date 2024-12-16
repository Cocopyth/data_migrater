#!/bin/bash

# To set up rclone, follow instructions at https://rclone.org/dropbox/
# Variables
REMOTE_PATH="shimizudbx:/DATA/PRINCE" # Replace with your rclone path
LOCAL_DEST="/mnt/sun-temp/TEMP/MOCK_ARETHA/"
# Ensure local destination directory exists
mkdir -p "$LOCAL_DEST"
echo "Clearing contents of $LOCAL_DEST..."
rm -rf "$LOCAL_DEST"/*
# List folders, sort by name, and select the first two
FOLDERS=$(rclone lsd "$REMOTE_PATH" | awk '{print $NF}' | sort | head -n 3)

# Download the selected folders and manually flatten the structure
for FOLDER in $FOLDERS; do
    echo "Downloading and flattening folder: $FOLDER"
    TEMP_DIR="/mnt/sun-temp/TEMP/temp/"
    # Temporary directory for intermediate download

    # Copy the folder into the temporary directory
    rclone copy "$REMOTE_PATH/$FOLDER" "$TEMP_DIR" --progress

    if [ $? -eq 0 ]; then
        echo "Successfully downloaded: $FOLDER"

        # Move files and subdirectories from TEMP_DIR to LOCAL_DEST (flattening the structure)
        find "$TEMP_DIR" -mindepth 1 -maxdepth 1 -exec mv -t "$LOCAL_DEST" {} +

        # Clean up the temporary directory
        rm -rf "$TEMP_DIR"

        # Check for and unzip files in LOCAL_DEST
    else
        echo "Error downloading: $FOLDER"
        rm -rf "$TEMP_DIR"  # Clean up in case of error
    fi
done

echo "First 2 folders processed with flattened structure!"
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