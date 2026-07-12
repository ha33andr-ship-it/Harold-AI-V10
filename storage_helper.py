import copy
import json
import os
from typing import Any, Dict

from google.api_core.exceptions import Forbidden, NotFound
from google.cloud import storage


BUCKET_NAME = os.getenv("BUCKET_NAME", "harold-ai-data")
STATE_OBJECT = "paper/paper_state.json"


def _get_bucket():
    client = storage.Client()
    return client.bucket(BUCKET_NAME)


def save_json(data: Dict[str, Any]) -> None:
    bucket = _get_bucket()
    blob = bucket.blob(STATE_OBJECT)

    blob.upload_from_string(
        json.dumps(data, indent=2),
        content_type="application/json",
    )


def load_json(default: Dict[str, Any]) -> Dict[str, Any]:
    bucket = _get_bucket()
    blob = bucket.blob(STATE_OBJECT)

    try:
        contents = blob.download_as_text()
        loaded = json.loads(contents)

        if not isinstance(loaded, dict):
            raise ValueError("Stored state is not a JSON object")

        return loaded

    except NotFound:
        new_state = copy.deepcopy(default)
        save_json(new_state)
        return new_state

    except (json.JSONDecodeError, ValueError):
        new_state = copy.deepcopy(default)
        save_json(new_state)
        return new_state

    except Forbidden as exc:
        raise RuntimeError(
            f"Cloud Run does not have permission to access bucket "
            f"'{BUCKET_NAME}'. Grant the service account Storage Object Admin."
        ) from exc
