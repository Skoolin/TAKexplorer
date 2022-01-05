import sys

# only works with size 6!!

def flip_tps(tps: str) -> str:
    spl = tps.split('/')
    spl.reverse()
    return '/'.join(spl)


def rotate_mat(board):
    result = []
    for i in range(0, len(board[0])):
        result.append(list(map(lambda x: x[i], board)))
    result.reverse()
    return result


def rotate_tps(tps: str) -> str:
    tps = tps.replace('x6', 'x,x,x,x,x,x')
    tps = tps.replace('x5', 'x,x,x,x,x')
    tps = tps.replace('x4', 'x,x,x,x')
    tps = tps.replace('x3', 'x,x,x')
    tps = tps.replace('x2', 'x,x')

    spl = tps.split('/')

    board = []

    for i in range(0, len(spl)):
        board.append(spl[i].split(','))

    board = rotate_mat(board)

    tps = '/'.join([','.join(a) for a in board])

    tps = tps.replace('x,x,x,x,x,x', 'x6')
    tps = tps.replace('x,x,x,x,x', 'x5')
    tps = tps.replace('x,x,x,x', 'x4')
    tps = tps.replace('x,x,x', 'x3')
    tps = tps.replace('x,x', 'x2')

    return tps


def get_tps_orientation(tps: str) -> int:
    # ignore ending (current player)
    tps = tps[:-4]

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
    return o


def transform_tps(tps: str, orientation: int) -> str:
    # remove current player and current move
    ending = tps[-4:]
    tps = tps[:-4]

    if orientation > 3:
        tps = flip_tps(tps)
        for i in range(4, orientation):
            tps = rotate_tps(tps)
    else:
        for i in range(0, orientation):
            tps = rotate_tps(tps)

    return tps + ending


def transposed_transform_tps(tps: str, orientation: int) -> str:
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

    for i in range(0, len(move)):
        if move[i].islower():
            return move[0:i] + rot_loc(move[i:i + 2]) + move[i + 2:]

    sys.exit(2)


def swapsquare(move):
    for i in range(0, len(move) - 1):
        if move[i].islower():
            return move[:i+1] + swapint(move[i + 1]) + move[i + 2:]


def transform_move(move: str, orientation: int) -> str:
    orig = move
    if orientation >= 4:
        move = swapchars(move, '+', '-')
        move = swapsquare(move)
    for i in range(0, orientation):
        move = rotate_move(move)
    test_transpose = transposed_transform_move(move, orientation)
    assert test_transpose == orig
    return move


def transposed_transform_move(move: str, orientation: int) -> str:
    for i in range(orientation, 4 if orientation >= 4 else 0, -1):
        move = rotate_move(move)
        move = rotate_move(move)
        move = rotate_move(move)
    if orientation >= 4:
        move = swapchars(move, '+', '-')
        move = swapsquare(move)
    return move
