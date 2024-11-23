import subprocess


def transfer_s3(local_file_path, s3_file_path):
    """
    Upload a file to an S3 bucket using rclone.

    Parameters:
    local_file_path (str): The path to the local file to be uploaded.
    s3_file_path (str): The destination path in the S3 bucket (e.g., "ceph-s3:bucket/path/file.txt").
    """

    # Construct the rclone copy command
    command = [
        "rclone",
        "copyto",
        local_file_path,  # Source file path
        s3_file_path,  # Destination S3 path
    ]
    print(command)
    # Execute the command
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Check if the command was successful
    if result.returncode == 0:
        print(f"File {local_file_path} uploaded to {s3_file_path} successfully.")
    else:
        print(f"Error occurred: {result.stderr.decode('utf-8')}")