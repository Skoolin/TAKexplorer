from abc import abstractmethod, ABC
from typing import Union

from tak import GameState


class PositionProcessor(ABC):

    @abstractmethod
    def add_game(self, size: int, playtak_id: int, white_name: str, black_name: str, ptn: str, result: str, rating_white: int, rating_black: int) -> int:
        pass

    @abstractmethod
    def add_position(self, game_id: int, move, result: str, tps: str, next_tps: Union[str, None], tak: GameState):
        pass
