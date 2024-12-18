from unittest.mock import AsyncMock

import pytest
from arq import Retry

from prince_archiver.entrypoints.exporter.worker import State, run_export
from prince_archiver.service_layer.dto import ExportImagingEvent
from prince_archiver.service_layer.handlers.export import ExportHandler


@pytest.fixture(name="workflow_payload")
def fixture_workflow_payload(metadata: dict) -> dict:
    return {
        "ref_id": "8b5b871a23454f9bb22b2e6fbae51764",
        "experiment_id": "test_id",
        "timestamp": "2001-01-01T00:00:00+00:00",
        "type": "stitch",
        "system": "prince",
        "local_path": "test/path",
        "metadata": metadata,
        "message_info": {
            "id": "test-id",
            "stream_name": "test-stream",
            "group_name": "test-group",
        },
    }


async def test_run_export_successful(
    workflow_payload: dict,
):
    export_handler = AsyncMock(ExportHandler)

    state = AsyncMock(State, export_handler=export_handler)
    ctx = {"state": state}

    await run_export(ctx, workflow_payload)

    expected_msg = ExportImagingEvent(**workflow_payload)

    export_handler.process.assert_awaited_once_with(expected_msg)


@pytest.mark.parametrize(
    "error_cls",
    (
        OSError,
        TimeoutError,
        ExceptionGroup("test", [OSError()]),
    ),
)
async def test_workflow_with_retries(workflow_payload: dict, error_cls: Exception):
    export_handler = AsyncMock(ExportHandler)
    export_handler.process.side_effect = error_cls

    state = AsyncMock(State, export_handler=export_handler)
    ctx = {"state": state}

    with pytest.raises(Retry):
        await run_export(ctx, workflow_payload)
