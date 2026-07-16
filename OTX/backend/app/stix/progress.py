from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Callable, Iterable, Iterator, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
_LOG_EVERY = 1000


def should_show_progress(enabled: bool | None) -> bool:
    if enabled is None:
        return sys.stderr.isatty()
    return enabled


def count_jsonl_records(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def track(
    iterable: Iterable[T],
    *,
    total: int | None = None,
    desc: str = "",
    unit: str = "it",
    enabled: bool | None = None,
    on_update: Callable[[int], None] | None = None,
) -> Iterator[T]:
    if not should_show_progress(enabled):
        for index, item in enumerate(iterable, start=1):
            if on_update:
                on_update(index)
            elif index == 1 or index % _LOG_EVERY == 0:
                suffix = f"/{total}" if total is not None else ""
                logger.info("%s: %s%s", desc or "Progress", index, suffix)
            yield item
        return

    try:
        from tqdm import tqdm
    except ImportError:
        for index, item in enumerate(iterable, start=1):
            if on_update:
                on_update(index)
            elif index == 1 or index % _LOG_EVERY == 0:
                suffix = f"/{total}" if total is not None else ""
                logger.info("%s: %s%s", desc or "Progress", index, suffix)
            yield item
        return

    with tqdm(
        iterable,
        total=total,
        desc=desc,
        unit=unit,
        file=sys.stderr,
        dynamic_ncols=True,
        mininterval=0.5,
    ) as bar:
        for item in bar:
            if on_update:
                on_update(bar.n)
            yield item


def log_phase(message: str, *, enabled: bool | None = None) -> None:
    if should_show_progress(enabled):
        try:
            from tqdm import tqdm

            tqdm.write(message, file=sys.stderr)
            return
        except ImportError:
            pass
    logger.info(message)
