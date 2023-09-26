from typing import NewType, Union, Literal


TpsSymmetry = NewType("TpsSymmetry", int)
TpsString = NewType("TpsString", str) # with xn collapsed (x,x,x,... -> xn)
TpsStringExpanded = NewType("TpsStringExpanded", str) # with xn expanded to x,x,x...
NormalizedTpsString = NewType("NormalizedTpsString", str)
BoardSize = NewType("BoardSize", int)
PlayerToMove = Union[Literal["white"], Literal["black"]]

def color_to_place_from_tps(tps: str) -> PlayerToMove:
    """
    The color of the next piece to place.
    After move 1 this equals the player that makes the move.
    """
    [_tps_str, player_to_move, move_counter] = tps.split(" ")
    player_to_move = "white" if player_to_move == "1" else "black"
    if int(move_counter) == 1:  # first move -> apply swap
        player_to_move = get_opponent(player_to_move)

    return player_to_move

def get_opponent(player_to_move: PlayerToMove) -> PlayerToMove:
    if player_to_move == "black":
        return "white"
    return "black"
