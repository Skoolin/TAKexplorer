class Stone:
    def __init__(self, colour: str, stone_type: str):
        self.colour = colour
        self.stone_type = stone_type

    def __str__(self):
        return self.stone_type if self.colour == "white" else self.stone_type.lower()

    def clone(self):
        return Stone(self.colour, self.stone_type)


class Square:
    def __init__(self):
        self.stones = []

    def __str__(self):
        # r = ''.join(map(str, self.stones))
        r = ''.join(self.stones)
        for _ in range(0, 8 - len(r)):
            r += ' '
        return r + '|'

    def clone(self):
        c = Square()
        c.stones = [stone.clone() for stone in self.stones]
        return c


def get_adjacent(square_idx: str, direction: str):
    x = ord(square_idx[0].lower())
    y = int(square_idx[1])
    if direction == '>':
        x += 1
    elif direction == '<':
        x -= 1
    elif direction == '+':
        y += 1
    elif direction == '-':
        y -= 1
    res = chr(x) + str(y)
    return res


class GameState:
    def __init__(self, size):
        self.board = []
        self.size = size
        for i in range(0, size):
            self.board.append([])
            for j in range(0, size):
                self.board[i].append(Square())
        self.player = "white"
        self.first_move = True

    def clone(self):
        c = GameState(self.size)
        c.player = self.player
        c.first_move = self.first_move
        for y in range(0, self.size):
            for x in range(0, self.size):
                c.board[x][y] = self.board[x][y].clone()
        return c

    def get_square(self, ptn: str):
        x = ord(ptn[0].lower()) - 97
        y = int(ptn[1]) - 1
        return self.board[x][y]

    def print_state(self):
        print('state:')
        for y in range(self.size - 1, -1, -1):
            res = ''
            for x in range(0, self.size):
                res += str(self.board[x][y])
            print(res)
        print('')

    def move(self, ptn: str):

        colour_to_place = self.player
        if self.first_move:
            colour_to_place = ("white" if self.player == "black" else "black")
            if self.player == "black":
                self.first_move = False

        # check for move command:
        first_char = ptn[0]
        move_command = first_char.isdecimal()
        stack_height = int(first_char) if move_command else 0

        if move_command:
            ptn = ptn[1:]
            square_idx = ptn[0:2]
            square = self.get_square(square_idx)

            s = []
            for _ in range(0, stack_height):
                s.append(square.stones.pop())
            direction = ptn[2]
            rest = ptn[3:]
            for drop_count in rest:
                square_idx = get_adjacent(square_idx, direction)
                square = self.get_square(square_idx)
                # flatten if top stone is wall
                try:
                    top_stone = square.stones.pop()
                    top_stone.stone_type = 'F'
                    square.stones.append(top_stone)
                except IndexError:
                    top_stone = None
                count = int(drop_count)
                for _ in range(0, count):
                    square.stones.append(s.pop())
            count = len(s)
            for _ in range(0, count):
                square.stones.append(s.pop())

        else:  # place command
            # check for special stones
            stone_type = 'F'
            if ptn[0].isupper():
                stone_type = ptn[0]
                ptn = ptn[1:]

            # get target square
            square = self.get_square(ptn)
            square.stones.append(Stone(colour_to_place, stone_type))

        # switch active player
        self.player = ("white" if self.player == "black" else "black")

    def get_tps(self):
        res = ''
        for y in range(self.size - 1, -1, -1):
            row = ''
            for x in range(0, self.size):
                square = self.board[x][y]
                if len(square.stones) == 0:
                    if len(row) > 0:
                        if row[-1].isnumeric() and len(row) > 1 and row[-2] == 'x':
                            row = row[0:-1] + str(int(row[-1]) + 1)
                        elif row[-1] == 'x':
                            row += '2'
                        else:
                            row += ',x'
                    else:
                        row += 'x'
                else:
                    if len(row) > 0:
                        row += ','
                    for stone in square.stones:
                        row += '1' if stone.colour == "white" else '2'
                        if stone.stone_type.lower() != 'f':
                            row += stone.stone_type.upper()
            res += row + '/'
        res = res[:-1] # remove trailing /
        res = res + (' 1' if self.player == "white" else ' 2') # add current player
        res = res + ' 1' #TODO: we don't count moves currently (also change in symmetry_normalisator.py)
        return res

    def reset(self):
        self.board = []
        for i in range(0, self.size):
            self.board.append([])
            for _ in range(0, self.size):
                self.board[i].append(Square())
        self.player = "white"
        self.first_move = True
