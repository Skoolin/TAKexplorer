from typing import Tuple

from base_types import BoardSize, NormalizedTpsString, TpsString, TpsStringExpanded, TpsSymmetry


def flip_tps(tps: TpsStringExpanded) -> TpsStringExpanded:
    spl = tps.split('/')
    spl.reverse()
    return TpsStringExpanded('/'.join(spl))


def rotate_mat(board: list[list[str]]) -> list[list[str]]:
    result: list[list[str]] = []
    for i in range(0, len(board[0])):
        result.append([x[i] for x in board])
    result.reverse()
    return result

def expand_tps_xn(tps: TpsString) -> TpsStringExpanded:
    s = tps.replace('x8', 'x,x,x,x,x,x,x,x')
    s = s.replace('x7', 'x,x,x,x,x,x,x')
    s = s.replace('x6', 'x,x,x,x,x,x')
    s = s.replace('x5', 'x,x,x,x,x')
    s = s.replace('x4', 'x,x,x,x')
    s = s.replace('x3', 'x,x,x')
    s = s.replace('x2', 'x,x')
    return TpsStringExpanded(s)

def collapse_tps_xn(tps: TpsStringExpanded) -> TpsString:
    s = tps.replace('x,x,x,x,x,x,x,x', 'x8')
    s = s.replace('x,x,x,x,x,x,x', 'x7')
    s = s.replace('x,x,x,x,x,x', 'x6')
    s = s.replace('x,x,x,x,x', 'x5')
    s = s.replace('x,x,x,x', 'x4')
    s = s.replace('x,x,x', 'x3')
    s = s.replace('x,x', 'x2')
    return TpsString(s)


def rotate_tps(tps_expanded: TpsStringExpanded) -> TpsStringExpanded:
    splits = tps_expanded.split('/')

    board: list[list[str]] = []

    for split in splits:
        board.append(split.split(','))

    board = rotate_mat(board)

    tps_expanded_rotated = '/'.join([','.join(a) for a in board])
    return TpsStringExpanded(tps_expanded_rotated)


def get_tps_orientation(tps: TpsString) -> Tuple[NormalizedTpsString, TpsSymmetry]:
    """
    nitzel 20230603: I've tried improving the performance by reducing the number
    of `NormalizedTpsString <-> list[list[str]]` conversions but that slowed it down instead.
    """
    # ignore ending (current player)
    tps = TpsString(tps[:-4])

    tps_expanded = expand_tps_xn(tps)
    o = 0
    best_tps = tps_expanded

    rot_tps = tps_expanded
    for i in range(1, 4):
        rot_tps = rotate_tps(rot_tps)
        if rot_tps < best_tps:
            o = i
            best_tps = rot_tps

    rot_tps = flip_tps(tps_expanded)
    if rot_tps < best_tps:
        o = 4
        best_tps = rot_tps
    for i in range(5, 8):
        rot_tps = rotate_tps(rot_tps)
        if rot_tps < best_tps:
            o = i
            best_tps = rot_tps
    return NormalizedTpsString(best_tps), TpsSymmetry(o)


def transform_tps(tps: TpsString, orientation: int) -> TpsString:
    # remove current player and current move
    ending = tps[-4:]
    tps = TpsString(tps[:-4])
    tps_expanded = expand_tps_xn(tps)
    if orientation > 3:
        tps_expanded = flip_tps(tps_expanded)
        for _ in range(4, orientation):
            tps_expanded = rotate_tps(tps_expanded)
    else:
        for _ in range(0, orientation):
            tps_expanded = rotate_tps(tps_expanded)

    tps_collapsed = TpsString(collapse_tps_xn(tps_expanded) + ending)
    return tps_collapsed


def transposed_transform_tps(tps: str, orientation: TpsSymmetry) -> str:
    # TODO
    return tps


def swapchars(s: str, a: str, b: str) -> str:
    """
    note: nitzel: This is very performant,
        iterating only once over the string via regex or list comprehension is ~4x slower
    """
    s = s.replace(a, 'z', 1)
    s = s.replace(b, a, 1)
    s = s.replace('z', b, 1)
    return s


def swapint(s: str, board_size: BoardSize) -> str:
    return str(int(s) * -1 + board_size + 1)


def rot_loc(location: str, board_size: BoardSize):
    col = location[0]
    row = int(location[1])
    new_row = ord(col) - ord('a') + 1  # column char to row number
    new_col = chr(ord('a') + board_size - row) # row number to column char
    return new_col + str(new_row)

def rotate_move(move: str, board_size) -> str:
    # a1 -> f1
    # 3c2+12 -> 3e3<12
    orig = move
    move = move.replace('+', 'z', 1)
    move = move.replace('>', '+', 1)
    move = move.replace('-', '>', 1)
    move = move.replace('<', '-', 1)
    move = move.replace('z', '<', 1)

    for (i, c) in enumerate(move):
        if c.islower():
            return move[0:i] + rot_loc(move[i:i + 2], board_size) + move[i + 2:]

    raise ValueError(f"Failed to rotate move orig='{orig}' on board_size={board_size} (result '{move}', no lower case)")



def swapsquare(move: str, board_size: BoardSize):
    for (i, c) in enumerate(move):
        if c.islower():
            return move[:i+1] + swapint(move[i + 1], board_size) + move[i + 2:]
    raise ValueError(f"Move '{move}' does not contain any lowercase characters and thus is no proper move")


def transform_move(move: str, orientation: TpsSymmetry, board_size: BoardSize) -> str:
    mirror: bool = orientation >= 4
    number_of_rotations: int = orientation - 4 if mirror else orientation
    # orig_move = move
    if mirror:
        move = swapchars(move, '+', '-')
        move = swapsquare(move, board_size)

    for _ in range(0, number_of_rotations):
        move = rotate_move(move, board_size)

    # Disabled for ~10% performance
    # test_transpose = transposed_transform_move(
    #     move=move,
    #     orientation=orientation,
    #     board_size=board_size
    # )
    # assert test_transpose == orig_move

    return move


def transposed_transform_move(move: str, orientation: TpsSymmetry, board_size: BoardSize) -> str:
    mirror: bool = orientation >= 4
    number_of_rotations: int = orientation - 4 if mirror else orientation

    for _ in range(number_of_rotations):
        move = rotate_move(move, board_size)
        move = rotate_move(move, board_size)
        move = rotate_move(move, board_size)

    if mirror:
        move = swapchars(move, '+', '-')
        move = swapsquare(move, board_size)
    return move
