"""Synchronous checkpoint adapter that refuses writes after operation-lock loss."""
from langgraph.checkpoint.base import BaseCheckpointSaver


class GuardedCheckpointer(BaseCheckpointSaver):
    def __init__(self, delegate, guard):
        super().__init__(serde=delegate.serde)
        self.delegate = delegate
        self.guard = guard

    @property
    def config_specs(self):
        return self.delegate.config_specs

    def get_tuple(self, config):
        return self.delegate.get_tuple(config)

    def list(self, config, **kwargs):
        yield from self.delegate.list(config, **kwargs)

    def get_next_version(self, current, channel):
        return self.delegate.get_next_version(current, channel)

    def put(self, *args, **kwargs):
        self.guard.check()
        return self.delegate.put(*args, **kwargs)

    def put_writes(self, *args, **kwargs):
        self.guard.check()
        return self.delegate.put_writes(*args, **kwargs)

    def delete_thread(self, *args, **kwargs):
        self.guard.check()
        return self.delegate.delete_thread(*args, **kwargs)
