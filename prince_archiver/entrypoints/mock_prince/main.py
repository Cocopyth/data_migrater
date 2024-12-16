import asyncio
import logging
from uuid import uuid4

import pytz
import redis.asyncio as redis


from prince_archiver.adapters.streams import Stream
from prince_archiver.definitions import EventType, System
from prince_archiver.log import configure_logging
from prince_archiver.service_layer.dto import NewImagingEvent
from prince_archiver.service_layer.streams import Message, Streams

from prince_archiver.entrypoints.mock_prince.util import  update_plate_info, get_current_folders

LOGGER = logging.getLogger(__name__)

REDIS_DSN = "redis://tsu-dsk001.ipa.amolf.nl:6380"



def _create_event(row) -> NewImagingEvent:
    ref_id = uuid4()
    timestamp = row["datetime"]

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
        system="prince",
        img_count=1,
        metadata={
            "application": {
                "application": "mock-prince",
                "version": "v0.1.0",
                "user": "mock-user",
            },
            "camera": {
                "model": "mock-model",
                "station_name": "mock-station",
                "exposure_time": 0.01,
                "frame_rate": None,
                "frame_size": (3000, 4096),
                "binning": "1x1",
                "gain": 1,
                "gamma": 1,
                "intensity": [0, 0, 0],
                "bits_per_pixel": 0,
            },
            "stitching": {
                "last_focused_at": "2000-01-01T00:00:00+00:00",
                "grid_size": (10, 15),
            },
        },
        local_path=f"Images/{row['folder']}",
    )


async def main():
    """Add new timestep directory every minute."""
    configure_logging()

    logging.info("Starting up mock prince")
    logging.info(REDIS_DSN)
    directory = "/dbx_copy/"
    update_plate_info(directory)
    run_info = get_current_folders(directory)
    client = redis.from_url(REDIS_DSN)
    async with client:
        pong = await client.ping()
        if pong:
            logging.info("Successfully connected to Redis")
        else:
            logging.error("Redis connection failed")
    async with client:
        stream = Stream(name='dlm:imaging-events', redis=client)
        for index, row in run_info.iterrows():
            meta = _create_event(row)
            logging.info(("posting", meta.ref_id))
            await asyncio.sleep(30)
            await stream.add(Message(meta))

if __name__ == "__main__":
    asyncio.run(main())
