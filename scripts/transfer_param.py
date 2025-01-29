import os
import shutil

# Define the base folder paths
param_base_path = r"/mnt/prince/ParamFiles/"
folder_base_path = r"/mnt/prince/"  # Update this to the path containing param files

# Define the correspondence dictionary (Update based on your data)
# Example: {'SCP2501D001': 'param_Plate01', 'COL2412A034': 'param_Plate02'}
id_to_param_mapping = {
    "SCP2501D001": "param_Plate01.m",
    # "COL2412A034": "param_Plate02",
    # "EPY2412A088": "param_Plate03",
    # Add other mappings here
}

# Iterate through the folders and process the files
for folder_name in os.listdir(folder_base_path):
    folder_id = folder_name.split("_")[-1]  # Extract ID from folder name
    if folder_id in id_to_param_mapping:
        param_file_name = id_to_param_mapping[folder_id]
        param_file_path = os.path.join(param_base_path, param_file_name)
        if os.path.exists(param_file_path):
            # Move and rename the param file
            destination_path = os.path.join(folder_base_path, folder_name, "param.m")
            shutil.move(param_file_path, destination_path)
            print(f"Moved {param_file_name} to {destination_path}")
        else:
            print(f"Param file {param_file_name} not found.")
    else:
        print(f"No mapping found for folder ID {folder_id}.")