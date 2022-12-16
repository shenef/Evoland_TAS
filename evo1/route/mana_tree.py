import contextlib
import logging
from enum import Enum, auto
from typing import Optional

from engine.mathlib import Vec2
from engine.seq import SeqBase, SeqList
from memory.evo1 import get_zelda_memory, load_zelda_memory
from memory.evo1.zephy import (
    ZephyrosGanonMemory,
    ZephyrosGolemMemory,
    ZephyrosPlayerMemory,
)
from term.window import WindowLayout

logger = logging.getLogger(__name__)


class ManaTree(SeqList):
    def __init__(self):
        super().__init__(
            name="Mana Tree",
            children=[
                # TODO: Fight final boss (Golem form)
                # TODO: Fight final boss (Ganon form)
            ],
        )


class ZephyrosGolemEntity:
    def __init__(self, mem: ZephyrosGolemMemory) -> None:
        self.rotation = mem.rotation
        self.hp_left_arm = mem.hp_left_arm
        self.hp_right_arm = mem.hp_right_arm
        self.hp_armor = mem.hp_armor
        self.hp_core = mem.hp_core
        self.anim_timer = mem.anim_timer

    @property
    def armless(self) -> bool:
        return self.hp_left_arm == 0 and self.hp_right_arm == 0

    @property
    def done(self) -> bool:
        return self.armless and self.hp_core == 0


class ZephyrosGanonEntity:
    def __init__(self, mem: ZephyrosGanonMemory) -> None:
        self.pos = mem.pos
        self.hp = mem.hp
        self.red_counter = mem.red_counter
        self.projectiles = mem.projectiles

    @property
    def done(self) -> bool:
        return self.hp == 0


class SeqZephyrosObserver(SeqBase):
    class FightState(Enum):
        NOT_STARTED = auto()
        STARTED = auto()
        GOLEM_SPAWNED = auto()
        GOLEM_FIGHT = auto()
        GOLEM_ARMLESS_SETUP = auto()
        GOLEM_ARMLESS_FIGHT = auto()
        GANON_WAIT = auto()
        GANON_FIGHT = auto()
        ENDING = auto()

    def __init__(self):
        super().__init__(
            name="Zephyros Observer",
            func=load_zelda_memory,
        )
        self.state = self.FightState.NOT_STARTED
        self.golem: Optional[ZephyrosGolemEntity] = None
        self.ganon: Optional[ZephyrosGanonEntity] = None
        self.player: Optional[ZephyrosPlayerMemory] = None
        self.dialog: int = 0
        self.dialog_cnt: int = 0

    def reset(self) -> None:
        self.state = self.FightState.NOT_STARTED
        self.golem: Optional[ZephyrosGolemEntity] = None
        self.ganon: Optional[ZephyrosGanonEntity] = None
        self.player: Optional[ZephyrosPlayerMemory] = None
        self.dialog: int = 0
        self.dialog_cnt: int = 0

    def _start_state(self) -> bool:
        return self.state in [
            self.FightState.NOT_STARTED,
            self.FightState.STARTED,
        ]

    def _golem_state(self) -> bool:
        return self.state in [
            self.FightState.GOLEM_SPAWNED,
            self.FightState.GOLEM_FIGHT,
            self.FightState.GOLEM_ARMLESS_SETUP,
            self.FightState.GOLEM_ARMLESS_FIGHT,
        ]

    def _ganon_state(self) -> bool:
        return self.state in [
            self.FightState.GANON_WAIT,
            self.FightState.GANON_FIGHT,
        ]

    _GOLEM_NUM_DIALOGS = 8
    _GANON_NUM_DIALOGS = 3
    _GOLEM_CORE_HP = 4
    _GANON_HP = 4

    def _update_state(self) -> None:
        mem = get_zelda_memory()

        match self.state:
            case self.FightState.NOT_STARTED | self.FightState.ENDING:
                self.player = None
            case _:
                self.player = mem.zephy_player

        # Handle initial cutscene part of the fight
        if self._start_state():
            match self.state:
                case self.FightState.NOT_STARTED:
                    if mem.in_zephy_fight:
                        self.state = self.FightState.STARTED
                        logger.info("Mana Tree entered.")

                case self.FightState.STARTED:
                    zephy = mem.zephy_golem(armless=False)
                    if zephy is not None:
                        self.state = self.FightState.GOLEM_SPAWNED
                        logger.info("Zephyros Golem spawned.")

        # Handle Golem fight state
        if self._golem_state():
            if self.state in [
                self.FightState.GOLEM_ARMLESS_SETUP,
                self.FightState.GOLEM_ARMLESS_FIGHT,
            ]:
                self.golem = ZephyrosGolemEntity(mem.zephy_golem(armless=True))
            else:
                self.golem = ZephyrosGolemEntity(mem.zephy_golem(armless=False))

            match self.state:
                case self.FightState.GOLEM_SPAWNED:
                    dialog = mem.zephy_dialog
                    # Count the dialog boxes
                    if dialog != self.dialog:
                        self.dialog = dialog
                        if dialog != 0:
                            self.dialog_cnt += 1
                        # If we have gotten enough text and dialog is 0, the fight is on
                        if self.dialog_cnt >= self._GOLEM_NUM_DIALOGS and dialog == 0:
                            logger.info("Zephyros Golem fight started.")
                            self.state = self.FightState.GOLEM_FIGHT
                case self.FightState.GOLEM_FIGHT:
                    if self.golem.armless:
                        logger.info("Zephyros Golem arms defeated.")
                        self.state = self.FightState.GOLEM_ARMLESS_SETUP
                case self.FightState.GOLEM_ARMLESS_SETUP:
                    if self.golem.hp_core == self._GOLEM_CORE_HP:
                        self.state = self.FightState.GOLEM_ARMLESS_FIGHT
                        logger.info("Zephyros Golem armless phase.")
                case self.FightState.GOLEM_ARMLESS_FIGHT:
                    if self.golem.done:
                        self.state = self.FightState.GANON_WAIT
                        self.dialog_cnt = 0
                        logger.info("Zephyros Golem defeated.")

        # Handle Ganon fight state
        if self._ganon_state():
            match self.state:
                case self.FightState.GANON_WAIT:
                    dialog = mem.zephy_dialog
                    if dialog != self.dialog:
                        self.dialog = dialog
                        if dialog != 0:
                            self.dialog_cnt += 1
                        # If we have gotten enough text and dialog is 0, the fight is on
                        if self.dialog_cnt >= self._GANON_NUM_DIALOGS and dialog == 0:
                            self.ganon = ZephyrosGanonEntity(mem.zephy_ganon)
                            self.state = self.FightState.GANON_FIGHT
                            logger.info("Zephyros Ganon fight started.")
                case self.FightState.GANON_FIGHT:
                    self.ganon = ZephyrosGanonEntity(mem.zephy_ganon)
                    if self.ganon.done:
                        self.state = self.FightState.ENDING
                        logger.info("Zephyros Ganon defeated.")

    def execute(self, delta: float) -> bool:
        super().execute(delta=delta)
        self._update_state()

        return False  # Never finishes

    def _render_player(self, window: WindowLayout) -> None:
        window.stats.addstr(pos=Vec2(1, 4), text=f"Player HP: {self.player.hp}")
        window.stats.addstr(
            pos=Vec2(2, 5),
            text=f"{self.player.polar}",
        )

    def _render_golem(self, window: WindowLayout) -> None:
        window.stats.addstr(
            pos=Vec2(1, 7), text=f"Golem theta={self.golem.rotation:.3f}"
        )
        window.stats.addstr(pos=Vec2(1, 8), text=f"Left arm: {self.golem.hp_left_arm}")
        window.stats.addstr(
            pos=Vec2(1, 9), text=f"Right arm: {self.golem.hp_right_arm}"
        )
        window.stats.addstr(pos=Vec2(1, 10), text=f"Armor: {self.golem.hp_armor}")
        window.stats.addstr(pos=Vec2(1, 11), text=f"Core: {self.golem.hp_core}")

    def _render_ganon(self, window: WindowLayout) -> None:
        zephy_pos = self.ganon.pos
        window.stats.addstr(pos=Vec2(1, 7), text=f"Zephy pos: {zephy_pos}")
        window.stats.addstr(pos=Vec2(1, 8), text=f"Zephy HP: {self.ganon.hp}")
        window.stats.addstr(pos=Vec2(1, 10), text="Projectiles:")
        with contextlib.suppress(ReferenceError):
            projectiles = [proj for proj in self.ganon.projectiles if proj.is_active]
            for i, proj in enumerate(projectiles):
                y = i + 11
                if y >= 15:
                    break
                blue = "blue" if proj.is_blue else "red"
                countered = ", counter!" if proj.is_countered else ""
                window.stats.addstr(
                    pos=Vec2(2, y), text=f"{proj.pos}, {blue}{countered}"
                )

    def render(self, window: WindowLayout) -> None:
        window.stats.erase()
        window.map.erase()

        window.stats.write_centered(line=1, text="Evoland TAS")
        window.stats.write_centered(line=2, text="Zephyros Battle")

        if self.player is not None:
            self._render_player(window=window)

        if self._golem_state():
            self._render_golem(window=window)
        elif self.state == self.FightState.GANON_FIGHT:
            self._render_ganon(window=window)
        elif self.state == self.FightState.ENDING:
            window.stats.write_centered(line=5, text="Good Game!")

    def __repr__(self) -> str:
        return f"Zephyros: {self.state.name}"
