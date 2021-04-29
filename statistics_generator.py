import json
from typing import Union

from position_processor import PositionProcessor
from tak import GameState


class StatisticsGenerator(PositionProcessor):
    def __init__(self, target_file: str):
        self.target_file = target_file
        self.ply = None
        self.result = None
        self.w_has_hard_cap = False
        self.b_has_hard_cap = False
        self.all_games = {'white': 0, 'black': 0, 'draw': 0}
        self.w_hard_cap_18 = {'white': 0, 'black': 0, 'draw': 0}
        self.b_hard_cap_18 = {'white': 0, 'black': 0, 'draw': 0}
        self.hard_cap_18 = [self.w_hard_cap_18, self.b_hard_cap_18]
        self.w_hard_cap_24 = {'white': 0, 'black': 0, 'draw': 0}
        self.b_hard_cap_24 = {'white': 0, 'black': 0, 'draw': 0}
        self.hard_cap_24 = [self.w_hard_cap_24, self.b_hard_cap_24]
        self.w_cap_12 = {'white': 0, 'black': 0, 'draw': 0}
        self.b_cap_12 = {'white': 0, 'black': 0, 'draw': 0}
        self.cap_12 = [self.w_cap_12, self.b_cap_12]
        self.w_cap_18 = {'white': 0, 'black': 0, 'draw': 0}
        self.b_cap_18 = {'white': 0, 'black': 0, 'draw': 0}
        self.cap_18 = [self.w_cap_18, self.b_cap_18]
        self.w_cap_24 = {'white': 0, 'black': 0, 'draw': 0}
        self.b_cap_24 = {'white': 0, 'black': 0, 'draw': 0}
        self.cap_24 = [self.w_cap_24, self.b_cap_24]

    def add_game(self, size: int, playtak_id: int, white_name: str, black_name: str, ptn: str, result: str,
                 rating_white: int, rating_black: int) -> int:
        self.reset_game_data(result)
        return 0

    def add_position(self, game_id: int, move, result: str, tps: str, next_tps: Union[str, None], tak: GameState):
        if move is None:
            return
        player = 0 if tak.player == 'white' else 1
        if move[0] == 'C':
            if self.ply < 12:
                self.cap_12[player][self.result] += 1
            elif self.ply < 18:
                self.cap_18[player][self.result] += 1
            else:
                self.cap_24[player][self.result] += 1
        if not self.w_has_hard_cap:
            for a in tak.board:
                for s in a:
                    l = len(s.stones)
                    if l > 1:
                        top = s.stones[-1]
                        below = s.stones[-1]
                        if top.colour == 'white' and below.colour == 'white' and top.stone_type == 'C':
                            self.w_has_hard_cap = True
                            if self.ply < 18:
                                self.hard_cap_18[0][self.result] += 1
                            else:
                                self.hard_cap_24[0][self.result] += 1
        elif not self.b_has_hard_cap:
            for a in tak.board:
                for s in a:
                    l = len(s.stones)
                    if l > 1:
                        top = s.stones[-1]
                        below = s.stones[-1]
                        if top.colour == 'black' and below.colour == 'black' and top.stone_type == 'C':
                            self.b_has_hard_cap = True
                            if self.ply < 18:
                                self.hard_cap_18[1][self.result] += 1
                            else:
                                self.hard_cap_24[1][self.result] += 1
        self.ply += 1

    def reset_game_data(self, result: str):
        self.ply = 0
        if (len(result) > 3) or (result[0] == result[2]):
            self.result = 'draw'
        else:
            self.result = 'white' if result[0] != '0' else 'black'
        self.w_has_hard_cap = False
        self.b_has_hard_cap = False
        self.all_games[self.result] += 1

    def print_results(self):
        f = open(self.target_file, 'w')
        json_obj = {
            'all_games': self.all_games,
            'w_hard_cap_18': self.w_hard_cap_18,
            'b_hard_cap_18': self.b_hard_cap_18,
            'w_hard_cap_24': self.w_hard_cap_24,
            'b_hard_cap_24': self.b_hard_cap_24,
            'w_cap_12': self.w_cap_12,
            'b_cap_12': self.b_cap_12,
            'w_cap_18': self.w_cap_18,
            'b_cap_18': self.b_cap_18,
            'w_cap_24': self.w_cap_24,
            'b_cap_24': self.b_cap_24,
        }
        for v in json_obj.values():
            v['white_win_percent'] = int(float(v['white']/(v['white']+v['black']))*100)
        json.dump(json_obj, f, indent=4)
        f.close()
