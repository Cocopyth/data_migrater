#!/bin/bash

# To set up rclone, follow instructions at https://rclone.org/dropbox/

# Check if the argument is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <j>"
    echo "Where <j> is the 1-based index of the folder to download."
    exit 1
fi

# Variables
REMOTE_PATH="shimizudbx:/DATA/PRINCE" # Replace with your rclone path
LOCAL_DEST="/mnt/sun-temp/TEMP/MOCK_ARETHA/"
FOLDER_INDEX=$1

# Ensure local destination directory exists
mkdir -p "$LOCAL_DEST"
echo "Removing files and directories older than 2 days in $LOCAL_DEST..."
find "$LOCAL_DEST" -mindepth 1 -ctime +2 -exec rm -rf {} +

# List folders, sort by name, and select the jth folder
FOLDERS=$(rclone lsd "$REMOTE_PATH" | awk '{print $NF}' | sort)
SELECTED_FOLDER=$(echo "$FOLDERS" | sed -n "${FOLDER_INDEX}p")

# Check if a valid folder was selected
if [ -z "$SELECTED_FOLDER" ]; then
    echo "Error: Invalid folder index $FOLDER_INDEX."
    echo "Available folders are:"
    echo "$FOLDERS"
    exit 1
fi

# Download the selected folder and manually flatten the structure
echo "Downloading and flattening folder: $SELECTED_FOLDER"
TEMP_DIR="/mnt/sun-temp/TEMP/temp/"  # Temporary directory for intermediate download

# Copy the folder into the temporary directory
rclone copy "$REMOTE_PATH/$SELECTED_FOLDER" "$TEMP_DIR"

if [ $? -eq 0 ]; then
    echo "Successfully downloaded: $SELECTED_FOLDER"

    # Move files and subdirectories from TEMP_DIR to LOCAL_DEST (flattening the structure)
    find "$TEMP_DIR" -mindepth 1 -maxdepth 1 -exec mv -t "$LOCAL_DEST" {} +

    # Clean up the temporary directory
    rm -rf "$TEMP_DIR"
else
    echo "Error downloading: $SELECTED_FOLDER"
    rm -rf "$TEMP_DIR"  # Clean up in case of error
    exit 1
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

echo "Folder $FOLDER_INDEX processed with flattened structure!"
