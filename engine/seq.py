# Libraries and Core Files
import datetime
import logging
import time
from typing import Any, Callable, List

from engine.mathlib import Vec2
from term.window import WindowLayout

logger = logging.getLogger(__name__)


class SeqBase(object):
    def __init__(self, name: str = "", func=None):
        self.name = name
        self.func = func

    def reset(self) -> None:
        pass

    def handle_input(self, input: str) -> None:
        pass

    # Return true if the sequence is done with, or False if we should remain in this state
    def execute(self, delta: float) -> bool:
        if self.func:
            self.func()
        return True

    def render(self, window: WindowLayout) -> None:
        pass

    # Should be overloaded
    def __repr__(self) -> str:
        return self.name


class SeqLog(SeqBase):
    def __init__(self, name: str, text: str):
        self.text = text
        super().__init__(name)

    def execute(self, delta: float) -> bool:
        logging.getLogger(self.name).info(self.text)
        return True


class SeqDebug(SeqBase):
    def __init__(self, name: str, text: str):
        self.text = text
        super().__init__(name)

    def execute(self, delta: float) -> bool:
        logging.getLogger(self.name).debug(self.text)
        return True


class SeqDelay(SeqBase):
    def __init__(self, name: str, timeout_in_s: float):
        self.timer = 0.0
        self.timeout = timeout_in_s
        super().__init__(name)

    def reset(self) -> None:
        self.timer = 0.0
        return super().reset()

    def execute(self, delta: float) -> bool:
        self.timer = self.timer + delta
        if self.timer >= self.timeout:
            self.timer = self.timeout
            return True
        return False

    def __repr__(self) -> str:
        return f"Waiting({self.name})... {self.timer:.2f}/{self.timeout:.2f}"


class SeqList(SeqBase):
    def __init__(
        self, name: str, children: List[SeqBase], func=None, shadow: str = False
    ):
        self.step = 0
        self.children = children
        self.shadow = shadow
        super().__init__(name, func=func)

    def reset(self) -> None:
        self.step = 0
        return super().reset()

    # Return true if the sequence is done with, or False if we should remain in this state
    def execute(self, delta: float) -> bool:
        super().execute(delta)
        num_children = len(self.children)
        if self.step >= num_children:
            return True
        cur_child = self.children[self.step]
        # Peform logic of current child step
        ret = cur_child.execute(delta=delta)
        if ret is True:  # If current child is done
            self.step = self.step + 1
        return False

    def render(self, window: WindowLayout) -> None:
        num_children = len(self.children)
        if self.step >= num_children:
            return
        cur_child = self.children[self.step]
        cur_child.render(window=window)

    def __repr__(self) -> str:
        num_children = len(self.children)
        if self.step >= num_children:
            return f"{self.name}[{num_children}/{num_children}]"
        cur_child = self.children[self.step]
        if self.shadow:
            return f"{cur_child}"
        cur_step = self.step + 1
        return f"{self.name}[{cur_step}/{num_children}] =>\n  {cur_child}"


class SeqOptional(SeqBase):
    def __init__(
        self,
        name: str,
        cases: dict[Any, SeqBase],
        selector: Callable | int,
        fallback: SeqBase = SeqBase(),
        shadow: bool = False,
    ):
        self.fallback = fallback
        self.selector = selector
        self.selector_repr = selector
        self.selected = False
        self.selection = None
        self.cases = cases
        self.shadow = shadow
        super().__init__(name)

    def reset(self) -> None:
        self.selected = False
        self.selection = None

    def execute(self, delta: float) -> bool:
        if not self.selected:
            self.selector_repr = (
                self.selector() if callable(self.selector) else self.selector
            )
            self.selection = self.cases.get(self.selector_repr)
            self.selected = True

        if self.selection:
            return self.selection.execute(delta=delta)
        if self.fallback:
            return self.fallback.execute(delta=delta)
        logging.getLogger(self.name).warning(
            f"Missing case {self.selector_repr} and no fallback, skipping!"
        )
        return True

    def render(self, window: WindowLayout) -> None:
        if self.selection:
            self.selection.render(window=window)
        elif self.fallback:
            self.fallback.render(window=window)

    def __repr__(self) -> str:
        if self.selection:
            if self.shadow:
                return f"{self.selection}"
            return f"<{self.name}:{self.selector_repr}> => {self.selection}"
        if self.selected and self.fallback:
            if self.shadow:
                return f"{self.fallback}"
            return f"<{self.name}:fallback> => {self.fallback}"
        return f"<{self.name}>"


class SequencerEngine(object):
    """
    Engine for executing sequences of generic TAS events.
    Each event sequence can be nested using SeqList.
    """

    def __init__(self, window: WindowLayout, root: SeqBase):
        self.window = window
        self.root = root
        self.done = False
        self.config = window.config_data
        self.paused = False
        self.timestamp = time.time()

    def reset(self) -> None:
        self.paused = False
        self.done = False
        self.root.reset()

    def pause(self) -> None:
        # TODO: Should restore controls to neutral state
        self.paused = True
        logger.info("------------------------")
        logger.info("  TAS EXECUTION PAUSED  ")
        logger.info("------------------------")

    def unpause(self) -> None:
        self.paused = False
        self.timestamp = time.time()
        logger.info("------------------------")
        logger.info(" TAS EXECUTION RESUMING ")
        logger.info("------------------------")

    def _handle_input(self) -> None:
        c = self.window.main.getch()
        # Keybinds: Pause TAS
        if c == ord("p"):
            paused = not self.paused
            if paused:
                self.pause()
            else:
                self.unpause()
        else:
            self.root.handle_input(c)

    def _get_deltatime(self) -> float:
        now = time.time()
        delta = now - self.timestamp
        self.timestamp = now
        return delta

    def _update(self) -> None:
        # Execute current gamestate logic
        if not self.paused and not self.done:
            delta = self._get_deltatime()
            self.done = self.root.execute(delta=delta)

    def _print_timer(self) -> None:
        # Timestamp
        start_time = logging._startTime
        now = time.time()
        elapsed = now - start_time
        duration = datetime.datetime.utcfromtimestamp(elapsed)
        timestamp = f"{duration.strftime('%H:%M:%S')}.{int(duration.strftime('%f')) // 1000:03d}"
        pause_str = " == PAUSED ==" if self.paused else ""
        self.window.main.addstr(Vec2(0, 0), f"[{timestamp}]{pause_str}")

    def _render(self) -> None:
        # Clear display windows
        self.window.main.erase()

        # Render timer and gamestate tree
        self._print_timer()
        self.window.main.addstr(Vec2(0, 1), f"Gamestate:\n  {self.root}")
        # Render the current gamestate
        self.root.render(window=self.window)

        self.window.update()

    # Execute and render TAS progress
    def run(self) -> None:
        self._handle_input()
        self._update()
        self._render()

    def active(self) -> bool:
        # Return current state of sequence engine (False when the game finishes)
        return not self.done
