import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
import pytz
import redis.asyncio as redis
from fastapi import FastAPI, Response
from pydantic import FilePath, RedisDsn
from pydantic_settings import BaseSettings

from prince_archiver.adapters.streams import Stream
from prince_archiver.definitions import EventType, System
from prince_archiver.log import configure_logging
from prince_archiver.service_layer.dto import NewImagingEvent
from prince_archiver.service_layer.streams import Message, Streams
from prince_archiver.test_utils.utils import make_timestep_directory
from prince_archiver.utils import now
from prince_archiver.entrypoints.mock_prince.util import  update_plate_info, get_current_folders

LOGGER = logging.getLogger(__name__)


class Settings(BaseSettings):
    INTERVAL: int = 30
    # DATA_DIR: Path
    REDIS_DSN: RedisDsn
    # SRC_IMG: FilePath


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
        system=System.PRINCE,
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
        local_path=row["total_path"],
    )


def create_app(*, settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    client = redis.from_url(str(settings.REDIS_DSN))

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        async with client:
            yield

    stream = Stream(name=Streams.imaging_events, redis=client)

    app = FastAPI(lifespan=lifespan)

    @app.post("/timestep", status_code=200)
    async def create_event(data: NewImagingEvent) -> Response:
        logging.info("[%s] Added timestep", data.ref_id)
        await stream.add(Message(data))

        return Response(status_code=200)

    return app


async def main():
    """Add new timestep directory every minute."""
    configure_logging()

    logging.info("Starting up mock prince")

    settings = Settings()

    transport = httpx.ASGITransport(app=create_app(settings=settings))
    directory = "/dbx_copy/"
    update_plate_info(directory)
    run_info = get_current_folders(directory)
    client = httpx.AsyncClient(transport=transport, base_url="http://mockprince")
    async with client:
        for index, row in run_info.iterrows():
            meta = _create_event(row)
            async with asyncio.TaskGroup() as tg:
                tg.create_task(asyncio.sleep(settings.INTERVAL))

                tg.create_task(
                    client.post(
                        "/timestep",
                        json=meta.model_dump(mode="json", by_alias=True),
                    )
                )


if __name__ == "__main__":
    asyncio.run(main())
