"""Utils for defining environement variables and defining paths"""

import json
import os
import re
from datetime import datetime

import numpy as np
import pandas as pd
from tqdm.autonotebook import tqdm



temp_path = "/mnt/sun-temp/TEMP"
if not os.path.exists(temp_path):
    os.mkdir(temp_path)


def get_param(
    folder, directory
):  # Very ugly but because interfacing with Matlab so most elegant solution.
    # TODO(FK)
    path_snap = os.path.join(directory, folder)
    file1 = open(os.path.join(path_snap, "param.m"), "r")
    Lines = file1.readlines()
    ldict = {}
    for line in Lines:
        to_execute = line.split(";")[0]
        relation = to_execute.split("=")
        if len(relation) == 2:
            ldict[relation[0].strip()] = relation[1].strip()
        # exec(line.split(';')[0],globals(),ldict)
    files = [
        "/Img/TileConfiguration.txt.registered",
        "/Analysis/skeleton.mat",
        "/Analysis/skeleton_masked.mat",
        "/Analysis/skeleton_pruned.mat",
        "/Analysis/transform.mat",
        "/Analysis/transform_corrupt.mat",
        "/Analysis/skeleton_pruned_realigned.mat",
        "/Analysis/nx_graph_pruned.p",
        "/Analysis/nx_graph_pruned_width.p",
        "/Analysis/nx_graph_pruned_labeled.p",
        "/Analysis/nx_graph_pruned_labeled2.p",
    ]
    for file in files:
        ldict[file] = os.path.isfile(path_snap + file)  # TODO(FK) change here
    return ldict



def update_plate_info(
    directory: str, local=True, strong_constraint=True, suffix_data_info=""
) -> None:
    """*
    1/ Download `data_info.json` file containing all information about acquisitions.
    2/ Add all acquisition files in the `directory` path to the `data_info.json`.
    3/ Upload the new version of data_info (actualised) to the dropbox.
    An acquisition repositorie has a param.m file inside it.
    """
    # TODO(FK): add a local version without dropbox modification
    listdir = os.listdir(directory)
    source = f"/data_info.json"
    target = os.path.join(temp_path, f"data_info{suffix_data_info}.json")
    plate_info = {}
    with tqdm(total=len(listdir), desc="analysed") as pbar:
        for folder in listdir:
            # print(folder)
            path_snap = os.path.join(directory, folder)
            if os.path.exists(os.path.join(path_snap, "Img")):
                sub_list_files = os.listdir(os.path.join(path_snap, "Img"))
                is_real_folder = os.path.isfile(os.path.join(path_snap, "param.m"))
                if strong_constraint:
                    is_real_folder *= (
                        os.path.isfile(
                            os.path.join(path_snap, "Img", "Img_r03_c05.tif")
                        )
                        * len(sub_list_files)
                        >= 100
                    )
                if is_real_folder:
                    params = get_param(folder, directory)
                    ss = folder.split("_")[0]
                    ff = folder.split("_")[1]
                    date = datetime(
                        year=int(ss[:4]),
                        month=int(ss[4:6]),
                        day=int(ss[6:8]),
                        hour=int(ff[0:2]),
                        minute=int(ff[2:4]),
                    )
                    params["date"] = datetime.strftime(date, "%d.%m.%Y, %H:%M:")
                    params["folder"] = folder
                    total_path = os.path.join(directory, folder)
                    plate_info[total_path] = params
            pbar.update(1)
    with open(target, "w") as jsonf:
        json.dump(plate_info, jsonf, indent=4)



def get_data_info(local=False, suffix_data_info=""):
    target = os.path.join(temp_path, f"data_info{suffix_data_info}.json")
    data_info = pd.read_json(target, convert_dates=True).transpose()
    if len(data_info) > 0:
        data_info.index.name = "total_path"
        data_info.reset_index(inplace=True)
        data_info["Plate"] = data_info["Plate"].fillna(0)
        data_info["unique_id"] = (
            data_info["Plate"]
            .astype(str)
            .str.replace(r"\D", "", regex=True)
            .astype(int)
            .astype(str)
            + "_"
            + data_info["CrossDate"].str.replace("'", "").astype(str)
        )

        data_info["datetime"] = pd.to_datetime(
            data_info["date"], format="%d.%m.%Y, %H:%M:"
        )
    return data_info





def get_current_folders(
    directory: str, local=True, suffix_data_info=""
) -> pd.DataFrame:
    """
    Returns a pandas data frame with all informations about the acquisition files
    inside the directory.
    WARNING: directory must finish with '/'
    """
    # TODO(FK): solve the / problem
    plate_info = get_data_info(local, suffix_data_info)
    listdir = os.listdir(directory)
    if len(plate_info) > 0:
        return plate_info.loc[
            np.isin(plate_info["folder"], listdir)
            & (plate_info["total_path"] == directory + plate_info["folder"])
        ]
    else:
        return plate_info


def parse_video_info(filepath):
    """Parses a single videoInfo.txt file into a dictionary."""
    info = {}
    with open(filepath, 'r', encoding='utf-8') as file:
        for line in file:
            # Ignore lines that are just dashes or blank
            if line.strip() == '' or set(line.strip()) == {'-'}:
                continue
            if ':' in line:
                key, value = line.split(':', 1)
                info[key.strip()] = value.strip()
    return info

def build_video_info_dataframe(root_dir):
    """
    Walks through all subdirectories of root_dir to find videoInfo.txt files,
    parses them, and returns a DataFrame with one row per file.
    """
    records = []

    for dirpath, _, filenames in os.walk(root_dir):
        if 'videoInfo.txt' in filenames:
            full_path = os.path.join(dirpath, 'videoInfo.txt')
            folder_name = os.path.basename(os.path.dirname(full_path))
            record = parse_video_info(full_path)
            record['folder_id'] = folder_name
            records.append(record)

    return pd.DataFrame(records)

def find_max_row_col(directory):
    """
    Finds the maximum row (yy) and column (xx) values from filenames in the specified directory.

    Parameters:
    directory (str): The path to the directory containing the image files.

    Returns:
    tuple: A tuple containing the maximum xx and yy values.
    """

    # Initialize variables to store the maximum values of xx and yy
    max_xx = 0
    max_yy = 0

    # Regular expression pattern to match filenames of the form Img_rxx_cyy.tif
    pattern = r"Img_r(\d+)_c(\d+)\.tif"

    # Iterate over all files in the directory
    k = 0
    for filename in os.listdir(directory):
        match = re.match(pattern, filename)
        if match:
            k+=1
            xx = int(match.group(1))
            yy = int(match.group(2))
            max_xx = max(max_xx, xx)
            max_yy = max(max_yy, yy)

    return k,(max_xx, max_yy)

PROCESSED_ROWS_FILE = os.path.join(temp_path,"processed_rows_video.csv")

def load_processed_rows():
    if os.path.exists(PROCESSED_ROWS_FILE):
        return pd.read_csv(PROCESSED_ROWS_FILE)
    print("creating file")
    return pd.DataFrame(columns=["folder","old_id","Morrison_id"])

def save_processed_rows(processed_rows):
    processed_rows.to_csv(PROCESSED_ROWS_FILE, index=False)