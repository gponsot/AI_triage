from functools import lru_cache

import pandas as pd

from backend.config import MTS_DIALOG_URL


@lru_cache
def _load_dataset() -> pd.DataFrame:
    return pd.read_csv(MTS_DIALOG_URL).sample(n=20)


def get_dialogue_count() -> int:
    return len(_load_dataset())


def list_observation_options() -> list[dict[str, int | str]]:
    df = _load_dataset()
    options: list[dict[str, int | str]] = []
    for index in range(len(df)):
        dialogue = str(df.iloc[index]["dialogue"])
        preview = " ".join(dialogue.split())[:72]
        if len(dialogue) > 72:
            preview += "..."
        options.append(
            {
                "index": index,
                "label": f"Case {index + 1}: {preview}",
            }
        )
    return options


def load_dialogue_by_index(index: int) -> str:
    df = _load_dataset()
    if index < 0 or index >= len(df):
        raise IndexError(
            f"Row index {index} is out of range. Dataset has {len(df)} rows (0-based)."
        )
    dialogue = df.iloc[index]["dialogue"]
    if pd.isna(dialogue):
        raise ValueError(f"Row {index} has an empty dialogue field.")
    return str(dialogue)
