import os
import subprocess
import sys
from datetime import datetime

import networkx as nx
import pandas as pd
from matplotlib import cm, pyplot as plt

from amftrack.pipeline.functions.image_processing.experiment_class_surf import (
    Experiment,
)
from amftrack.pipeline.functions.image_processing.experiment_util import get_dimX_dimY
from amftrack.util.geometry import get_bounding_box
from amftrack.util.graph_format_manipulation import add_positions_to_nodes, write_graph_to_geojson
from amftrack.util.sys import temp_path, update_plate_info, get_current_folders
from util import transfer_s3

directory = "/media/admincorentin/5644166e-8493-472e-9f2e-a710ced69b0b/dbx_copy/"
update_plate_info(directory)
run_info = get_current_folders(directory)

folder_list = list(run_info["folder"])
folder_list.sort()
path_rclone = "shimizudbx:/DATA/PRINCE_VISU"
for i in range(len(folder_list)):
# for i in range(2):
    directory_name = folder_list[i]
    print(directory_name)

    exp = Experiment(directory)
    folder = run_info.loc[run_info["folder"] == directory_name]
    path = folder["total_path"].iloc[0]

    local_file_path = os.path.join(path, "Analysis","nx_graph_pruned_labeled.p")
    if os.path.exists(local_file_path):
        exp.load(folder, suffix="_labeled", has_datetime=False)
        (G, pos) = exp.nx_graph[0], exp.positions[0]
        t = 0
        DIM_X, DIM_Y = get_dimX_dimY(exp)

        image_coodinates = exp.image_coordinates[t]
        region = get_bounding_box(image_coodinates)
        region[1][0] += DIM_X
        region[1][1] += DIM_Y
        edgelist = list(G.edges())
        widths = [
            G[node1][node2]["width"]
            for node1, node2 in edgelist
        ]
        max_width = 10
        min_width = 3
        print(max_width, min_width)
        colors = [
            cm.plasma((width - min_width) / (max_width - min_width))
            for width in widths
        ]
        fig, ax = plt.subplots()
        rotated_pos = {node: (y, -x) for node, (x, y) in pos.items()}
        nx.draw_networkx(
            G,
            pos=rotated_pos,
            with_labels=False,
            nodelist=[],  # Set the nodes corresponding to the edges
            edgelist=edgelist,
            edge_color=colors,
            width=0.5
        )
        plt.gca().set_aspect('equal')
        plt.xlim(0, region[1][1])  # Set x-axis limits
        plt.ylim(-region[1][0], 0)  # Set y-axis limits
        ax.set_facecolor('black')
        row = folder.iloc[0]
        path = row['total_path']
        local_file_path = os.path.join(path, "graph.png")
        plt.savefig(local_file_path, dpi=400)  # Zero-padded for easier sorting
        add_positions_to_nodes(G, pos)
        local_file_path = os.path.join(path, "graph.geojson")
        write_graph_to_geojson(G, local_file_path)

for index, row in run_info.iterrows():
    print(row)
    path = row["total_path"]
    experiment_id = row["unique_id"]
    experiment_id = str(experiment_id)
    timestamp_obj = row["datetime"]
    # timestamp_obj = datetime.fromisoformat(timestamp_str)
    formatted_timestamp = timestamp_obj.strftime("%Y%m%d_%H%M")
    timestep_id = formatted_timestamp

    local_file_path = os.path.join(path, "graph.png")
    #TODO: Factorize this and graph uploader and others
    if os.path.exists(local_file_path):
        transfer_s3(
            local_file_path,
            f"{path_rclone}/{experiment_id}/visu/graph/{formatted_timestamp}.png",
        )
        local_file_path = os.path.join(path, "graph.geojson")
        transfer_s3(
            local_file_path,
            f"{path_rclone}/{experiment_id}/data/{formatted_timestamp}_{timestep_id}graph.geojson",
        )
    # break

