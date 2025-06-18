import asyncio
import logging
from uuid import uuid4
import sys
import subprocess
import os

import pandas as pd
import pytz
import redis.asyncio as redis


from prince_archiver.adapters.streams import Stream
from prince_archiver.definitions import EventType
from prince_archiver.log import configure_logging
from prince_archiver.service_layer.dto import NewImagingEvent
from prince_archiver.service_layer.streams import Message

from prince_archiver.entrypoints.mock_prince.util import update_plate_info, get_current_folders, find_max_row_col, \
    load_processed_rows, save_processed_rows, build_video_info_dataframe

LOGGER = logging.getLogger(__name__)

REDIS_DSN = "redis://tsu-dsk001.ipa.amolf.nl:6380"

script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the script's directory
file_path = os.path.join(script_dir, "2025_DataMigration_video.xlsx")
data_migration = pd.read_excel(file_path)

# Create a mapping dictionary from OLD_UI to UI
id_mapping = dict(zip(data_migration['OLD_UI'], data_migration['UI']))

# Run the command


def _create_event(row) -> NewImagingEvent:
    ref_id = uuid4()
    timestamp = row["datetime"]
    img_path = os.path.join(row["total_path"],"Img")
    img_count,grid_size = find_max_row_col(img_path)
    # Convert the timestamp to a naive datetime
    naive_timestamp = timestamp.to_pydatetime()

    # Define the Amsterdam timezone
    amsterdam_timezone = pytz.timezone("Europe/Amsterdam")

    # Localize the naive datetime to the Amsterdam timezone
    aware_timestamp = amsterdam_timezone.localize(naive_timestamp)

    # Use the aware_timestamp in your NewImagingEvent
    timestamp = aware_timestamp
    return NewImagingEvent(
        ref_id=ref_id,
        experiment_id=row["unique_id"],
        timestamp=timestamp,
        type=EventType.STITCH,
        system="tsu-exp002",
        img_count=img_count,
        metadata={
            "application": {
                "application": "mock-prince",
                "version": "v0.1.0",
                "user": "mock-user",
            },
            "camera": {
                "model": "Basler acA4112-20um SN:40193936",
                "station_name": f"#{row['PrincePos']}",
                "exposure_time": 0.1,
                "frame_rate": None,
                "frame_size": (4096, 3000),
                "binning": "1x1",
                "gain": 0.0,
                "gamma": 1,
                "intensity": [0],
                "bits_per_pixel": 8,
            },
            "stitching": {
                "last_focused_at": None,
                "grid_size": grid_size,
            },
        },
        local_path=f"Images/{row['folder']}/Img",
    )


async def main(directory):
    """Add new timestep directory every minute."""
    processed_rows = load_processed_rows()
    for ind,row_ids in data_migration.iterrows():
        unid = row_ids["OLD_UI"]
        if row_ids["Morrison_id"] not in processed_rows['Morrison_id'].unique():
            command = f'bash /home/ipausers/bisot/data_migrater/scripts/download_specific2.sh {unid}'
            try:
                subprocess.run(command, shell=True, check=True)
                print("Command executed successfully!")
            except subprocess.CalledProcessError as e:
                print(f"Command failed with error: {e}")
            configure_logging()

            logging.info("Starting up mock prince")
            logging.info(REDIS_DSN)
            # directory = "/dbx_copy/"
            run_info = build_video_info_dataframe(directory)
            if len(run_info)>0:
                new_rows = run_info[~run_info["DateTime"].isin(processed_rows["DateTime"])]
                new_rows = new_rows.sort_values(by = 'datetime')
                new_rows = new_rows.sort_values(by = 'unique_id')
                client = redis.from_url(REDIS_DSN)
                async with client:
                    pong = await client.ping()
                    if pong:
                        logging.info("Successfully connected to Redis")
                    else:
                        logging.error("Redis connection failed")
                async with client:
                    stream = Stream(name='dlm:new-imaging-event', redis=client,max_len = 10000)
                    for index, row in new_rows.iterrows():
                        old_id = row['unique_id']
                        if old_id in id_mapping:
                            row['unique_id'] = id_mapping[old_id]
                            row['old_id'] = old_id

                        meta = _create_event(row)
                        logging.info(("posting", meta.ref_id))
                        await stream.add(Message(meta))
                        processed_rows = pd.concat([processed_rows, pd.DataFrame([row])], ignore_index=True)
                        save_processed_rows(processed_rows)
                        await asyncio.sleep(1)
                    await asyncio.sleep(60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <directory>")
        sys.exit(1)
    directory = sys.argv[1]
    asyncio.run(main(directory))
