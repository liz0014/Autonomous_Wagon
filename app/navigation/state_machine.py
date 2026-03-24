"""
state_machine.py
----------------
Simple FSM that wraps follow_logic output into wagon-level states.
Extend this as new behaviours are added (obstacle avoidance, docking, etc.).

States
------
SEARCH  = no person visible, rotate/scan
FOLLOW  = person visible, drive toward them
STOP    = person too close, hold position
"""

from enum import Enum, auto


class WagonState(Enum):
    SEARCH = auto()
    FOLLOW = auto()
    STOP   = auto()


_CMD_TO_STATE = {
    "SEARCH": WagonState.SEARCH,
    "FOLLOW": WagonState.FOLLOW,
    "STOP":   WagonState.STOP,
}


class StateMachine:
    def __init__(self):
        self.state = WagonState.SEARCH

    def update(self, cmd: str) -> WagonState:
        """Transition based on follow_logic command string."""
        self.state = _CMD_TO_STATE.get(cmd, WagonState.SEARCH)
        return self.state

    @property
    def name(self) -> str:
        return self.state.name