import os
import shutil

# Define the base folder paths
param_base_path = r"/mnt/prince/ParamFiles/"
folder_base_path = r"/mnt/prince/"  # Update this to the path containing param files

# Define the correspondence dictionary (Update based on your data)
# Example: {'SCP2501D001': 'param_Plate01', 'COL2412A034': 'param_Plate02'}
id_to_param_mapping = {
    "SCP2501D001": "param_Plate01.m",
    "COL2412A034": "param_Plate20.m",
    "ART2501A044": "param_Plate02.m",
    "SCP2501D006": "param_Plate05.m",
    "COL2412A031": "param_Plate07.m",
    # "CTA2412A022": "param_Plate20.m",
    "COL2412A039": "param_Plate09.m",
    "ART2412A026": "param_Plate10.m",
    "SCP2501D010": "param_Plate11.m",
    "SCP2501D012": "param_Plate12.m",
    "EPY2412A088": "param_Plate13.m",
    "COL2412A035": "param_Plate14.m",
    "COL2412A041": "param_Plate19.m",
    "COL2412A043": "param_Plate21.m",
    "SCP2501D007": "param_Plate03.m",
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
            shutil.copy(param_file_path, destination_path)
            print(f"Moved {param_file_name} to {destination_path}")
        else:
            print(f"Param file {param_file_name} not found.")
    else:
        print(f"No mapping found for folder ID {folder_id}.")