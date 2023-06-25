import sys
from typing import NewType, Tuple

TpsSymmetry = NewType("TpsSymmetry", int)
TpsString = NewType("TpsString", str) # with xn collapsed (x,x,x,... -> xn)
TpsStringExpanded = NewType("TpsStringExpanded", str) # with xn expanded to x,x,x...
NormalizedTpsString = NewType("NormalizedTpsString", str)

# only works with size 6!!

def flip_tps(tps: TpsStringExpanded) -> TpsStringExpanded:
    spl = tps.split('/')
    spl.reverse()
    return '/'.join(spl)  # type: ignore


def rotate_mat(board):
    result = []
    for i in range(0, len(board[0])):
        result.append([x[i] for x in board])
    result.reverse()
    return result

def expand_tps_xn(tps: TpsString) -> TpsStringExpanded:
    tps = tps.replace('x6', 'x,x,x,x,x,x') # type: ignore
    tps = tps.replace('x5', 'x,x,x,x,x') # type: ignore
    tps = tps.replace('x4', 'x,x,x,x') # type: ignore
    tps = tps.replace('x3', 'x,x,x') # type: ignore
    tps = tps.replace('x2', 'x,x') # type: ignore
    return tps # type: ignore

def collapse_tps_xn(tps: TpsStringExpanded) -> TpsString:
    tps = tps.replace('x6', 'x,x,x,x,x,x') # type: ignore
    tps = tps.replace('x5', 'x,x,x,x,x') # type: ignore
    tps = tps.replace('x4', 'x,x,x,x') # type: ignore
    tps = tps.replace('x3', 'x,x,x') # type: ignore
    tps = tps.replace('x2', 'x,x') # type: ignore
    return tps # type: ignore


def rotate_tps(tps_expanded: TpsStringExpanded) -> TpsStringExpanded:
    splits = tps_expanded.split('/')

    board = []

    for split in splits:
        board.append(split.split(','))

    board = rotate_mat(board)

    tps_expanded_rotated: TpsStringExpanded = '/'.join([','.join(a) for a in board]) # type: ignore

    return tps_expanded_rotated


def get_tps_orientation(tps: TpsString) -> Tuple[NormalizedTpsString, TpsSymmetry]:
    # ignore ending (current player)
    tps = tps[:-4] # type: ignore

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
    normalized_tps: NormalizedTpsString = best_tps # type: ignore
    return normalized_tps, TpsSymmetry(o)


def transform_tps(tps: TpsString, orientation: int) -> TpsString:
    # remove current player and current move
    ending = tps[-4:]
    tps = tps[:-4] # type: ignore
    tps_expanded = expand_tps_xn(tps)
    if orientation > 3:
        tps_expanded = flip_tps(tps_expanded)
        for _ in range(4, orientation):
            tps_expanded = rotate_tps(tps_expanded)
    else:
        for _ in range(0, orientation):
            tps_expanded = rotate_tps(tps_expanded)

    tps_collapsed: TpsString = collapse_tps_xn(tps_expanded) + ending # type: ignore
    return tps_collapsed


def transposed_transform_tps(tps: str, orientation: TpsSymmetry) -> str:
    # TODO
    return tps


def swapchars(s: str, a: str, b: str) -> str:
    """
    note: nitzel: This is very performant,
        iterating only once over the string via regex or list comprehension is ~4x slower
    """
    s = s.replace(a, 'z')
    s = s.replace(b, a)
    s = s.replace('z', b)
    return s


def swapint(s: str) -> str:
    return str(int(s) * -1 + 7)


def rot_loc(location: str):
    col = location[0]
    row = int(location[1])
    new_row = ord(col) - ord('a') + 1  # column char to row number
    new_col = 'fedcba'[row-1] # row number to column char
    return new_col + str(new_row)

def rotate_move(move: str) -> str:
    # a1 -> f1
    # 3c2+12 -> 3e3<12
    move = move.replace('+', 'z')
    move = move.replace('>', '+')
    move = move.replace('-', '>')
    move = move.replace('<', '-')
    move = move.replace('z', '<')

    for (i, c) in enumerate(move):
        if c.islower():
            return move[0:i] + rot_loc(move[i:i + 2]) + move[i + 2:]

    sys.exit(2)


def swapsquare(move: str):
    for (i, c) in enumerate(move):
        if c.islower():
            return move[:i+1] + swapint(move[i + 1]) + move[i + 2:]
    raise ValueError(f"Move '{move}' does not contain any lowercase characters and thus is no proper move")


def transform_move(move: str, orientation: TpsSymmetry) -> str:
    orig = move
    if orientation >= 4:
        move = swapchars(move, '+', '-')
        move = swapsquare(move)
    for _ in range(0, orientation):
        move = rotate_move(move)
    test_transpose = transposed_transform_move(move, orientation)
    assert test_transpose == orig
    return move


def transposed_transform_move(move: str, orientation: TpsSymmetry) -> str:
    for _ in range(orientation, 4 if orientation >= 4 else 0, -1):
        move = rotate_move(move)
        move = rotate_move(move)
        move = rotate_move(move)
    if orientation >= 4:
        move = swapchars(move, '+', '-')
        move = swapsquare(move)
    return move
