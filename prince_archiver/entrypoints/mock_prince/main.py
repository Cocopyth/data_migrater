import asyncio
import logging
from uuid import uuid4
import sys
import subprocess
import os
from datetime import datetime

import pandas as pd
import pytz
import redis.asyncio as redis


from prince_archiver.adapters.streams import Stream
from prince_archiver.definitions import EventType
from prince_archiver.log import configure_logging
from prince_archiver.service_layer.dto import NewImagingEvent
from prince_archiver.service_layer.dto.common import Metadata
from prince_archiver.service_layer.streams import Message

from prince_archiver.entrypoints.mock_prince.util import update_plate_info, get_current_folders, find_max_row_col, \
    load_processed_rows, save_processed_rows, build_video_info_dataframe, parse_exposure_time, parse_frame_size, \
    extract_magnification_and_type, extract_img_count, process_dataframe_with_video_nr

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
    date_str= row["DateTime"]
    # Convert the timestamp to a naive datetime
    dt_obj = datetime.strptime(date_str, "%A, %d %B %Y, %H:%M:%S")

    # Optionally convert to pandas.Timestamp
    timestamp = pd.to_datetime(dt_obj)

    # Convert to naive Python datetime object
    naive_timestamp = timestamp.to_pydatetime()

    # Define the Amsterdam timezone
    amsterdam_timezone = pytz.timezone("Europe/Amsterdam")

    # Localize the naive datetime to the Amsterdam timezone
    aware_timestamp = amsterdam_timezone.localize(naive_timestamp)

    # Use the aware_timestamp in your NewImagingEvent
    timestamp = aware_timestamp
    exposure_time = parse_exposure_time(row["ExposureTime"])
    frame_size = parse_frame_size(row["FrameSize"])
    magnification, video_type = extract_magnification_and_type(row.get("Operation", ""))

    metadata = Metadata(
        application={
            "application": "mock-morrison",
            "version": "v0.1.0",
            "user": "mock-user",
        },
        camera={
            "model": row["Model"],
            "station_name": row.get("StationName", "Unknown"),
            "exposure_time": exposure_time,
            "frame_rate": float(row["FrameRate"].split()[0]),
            "frame_size": frame_size,
            "bits_per_pixel": 8,  # hardcoded; adjust if needed
            "binning": row["Binning"],
            "gain": float(row["Gain"]),
            "gamma": float(row["Gamma"]),
            "intensity": [0],  # Placeholder; use real values if available
            "pixel_size": 1.725
        },
        video={
            "duration": int(row["Time"].split()[0]),
            "location": [float(row["X"].split()[0]), float(row["Y"].split()[0]), float(row["Z"].split()[0])],
            "magnification": magnification,
            "type": video_type,
            "video_nr": row["video_nr"],
        },
    )

    return NewImagingEvent(
        ref_id=ref_id,
        experiment_id=row["unique_id"],
        timestamp=timestamp,
        type=EventType.VIDEO,
        img_count=extract_img_count(row["Frames Recorded"]),  # placeholder; ideally extract from "Frames Recorded"
        system="tsu-exp002",
        metadata=metadata,
        local_path=f"Images/{row['folder']}/Img"
    )


async def main(directory):
    """Add new timestep directory every minute."""
    processed_rows = load_processed_rows()
    for ind,row_ids in data_migration.iterrows():
        unid = row_ids["UI"]
        mor_id = row_ids["Morrison_id"]
        if row_ids["Morrison_id"] not in processed_rows['Morrison_id'].unique():
            # This currently doesn't work because Morrison id is not correctly set by build_video_info_dataframe
            command = f'bash /home/ipausers/bisot/data_migrater/scripts/download_specific2.sh {mor_id}'
            try:
                # subprocess.run(command, shell=True, check=True)
                print("Command executed successfully!")
            except subprocess.CalledProcessError as e:
                print(f"Command failed with error: {e}")
            configure_logging()

            logging.info("Starting up mock prince")
            logging.info(REDIS_DSN)
            # directory = "/dbx_copy/"
            run_info = build_video_info_dataframe(directory)
            run_info["unique_id"] = run_info.apply(lambda row: f"{row['Plate']}_{row['DateTime']}", axis=1)  # You define this
            df = process_dataframe_with_video_nr(df)
            if len(run_info)>0:
                # new_rows = run_info #Test mode
                new_rows = run_info[~run_info["DateTime"].isin(processed_rows["DateTime"])]
                new_rows = new_rows.sort_values(by = 'DateTime')
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
                        row['unique_id'] = unid
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
