"""Micro-batch stream aggregator for pipelining chunks into extraction and indexing."""

from collections.abc import AsyncIterator, Sequence
from typing import TypeVar

T = TypeVar("T")


class MicroBatcher:
    """Groups item streams into micro-batches to maximize GPU utilization without RAM spikes."""

    def __init__(self, batch_size: int = 16) -> None:
        self.batch_size = batch_size

    def create_batches(self, items: Sequence[T]) -> list[list[T]]:
        """Slice contiguous items into batches of up to batch_size."""
        return [list(items[i : i + self.batch_size]) for i in range(0, len(items), self.batch_size)]

    async def stream_batches(self, item_stream: AsyncIterator[T]) -> AsyncIterator[list[T]]:
        """Asynchronously stream micro-batches as items arrive."""
        current_batch: list[T] = []
        async for item in item_stream:
            current_batch.append(item)
            if len(current_batch) >= self.batch_size:
                yield current_batch
                current_batch = []
        if current_batch:
            yield current_batch


batcher = MicroBatcher()
