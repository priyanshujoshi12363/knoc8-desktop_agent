from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Action:
    func: Callable[..., str]
    desc: str
    params: dict[str, str] = field(default_factory=dict)
    dangerous: bool = False

    def run(self, **kwargs) -> str:
        allowed = self.func.__code__.co_varnames[: self.func.__code__.co_argcount]
        clean = {k: v for k, v in kwargs.items() if k in allowed}
        return self.func(**clean)
