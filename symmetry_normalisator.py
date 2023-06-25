import sys
from typing import NewType, Tuple

TpsSymmetry = NewType("TpsSymmetry", int)
TpsString = NewType("TpsString", str)
NormalizedTpsString = NewType("NormalizedTpsString", str)

# only works with size 6!!

def flip_tps(tps: TpsString) -> TpsString:
    spl = tps.split('/')
    spl.reverse()
    return '/'.join(spl)  # type: ignore


def rotate_mat(board):
    result = []
    for i in range(0, len(board[0])):
        result.append([x[i] for x in board])
    result.reverse()
    return result


def rotate_tps(tps: TpsString) -> TpsString:
    # todo improve performance by not reverting xn->x,x,x
    tps = tps.replace('x6', 'x,x,x,x,x,x') # type: ignore
    tps = tps.replace('x5', 'x,x,x,x,x') # type: ignore
    tps = tps.replace('x4', 'x,x,x,x') # type: ignore
    tps = tps.replace('x3', 'x,x,x') # type: ignore
    tps = tps.replace('x2', 'x,x') # type: ignore

    splits = tps.split('/')

    board = []

    for split in splits:
        board.append(split.split(','))

    board = rotate_mat(board)

    tps = '/'.join([','.join(a) for a in board]) # type: ignore

    tps = tps.replace('x,x,x,x,x,x', 'x6') # type: ignore
    tps = tps.replace('x,x,x,x,x', 'x5') # type: ignore
    tps = tps.replace('x,x,x,x', 'x4') # type: ignore
    tps = tps.replace('x,x,x', 'x3') # type: ignore
    tps = tps.replace('x,x', 'x2') # type: ignore

    return tps


def get_tps_orientation(tps: TpsString) -> Tuple[NormalizedTpsString, TpsSymmetry]:
    # ignore ending (current player)
    tps = tps[:-4] # type: ignore

    o = 0
    best_tps = tps

    rot_tps = tps
    for i in range(1, 4):
        rot_tps = rotate_tps(rot_tps)
        if rot_tps < best_tps:
            o = i
            best_tps = rot_tps

    rot_tps = flip_tps(tps)
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


def transform_tps(tps: TpsString, orientation: int) -> str:
    # remove current player and current move
    ending = tps[-4:]
    tps = tps[:-4] # type: ignore

    if orientation > 3:
        tps = flip_tps(tps)
        for _ in range(4, orientation):
            tps = rotate_tps(tps)
    else:
        for _ in range(0, orientation):
            tps = rotate_tps(tps)

    return tps + ending


def transposed_transform_tps(tps: str, orientation: TpsSymmetry) -> str:
    # TODO
    return tps


def swapchars(s: str, a: str, b: str) -> str:
    s = s.replace(a, 'z')
    s = s.replace(b, a)
    s = s.replace('z', b)
    return s


def swapint(s: str) -> str:
    return str(int(s) * -1 + 7)


def rot_loc(location: str):
    c = location[0]
    i = int(location[1])
    newi = str('abcdef'.index(c)+1)
    newc = 'fedcba'[i-1]
    return newc+newi


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
    for i in range(0, len(move) - 1):
        if move[i].islower():
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
