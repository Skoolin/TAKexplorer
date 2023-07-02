import pytest
from base_types import BoardSize, TpsSymmetry
import symmetry_normalisator as symnorm

location_rotations: dict[int, list[tuple[str, str]]] = {
    BoardSize(6): [
        ("a1", "f1"),
        ("a2", "e1"),
        ("a3", "d1"),
        ("b1", "f2"),
        ("b2", "e2"),
        ("b3", "d2"),
    ],
    BoardSize(7): [
        ("a1", "g1"),
        ("a2", "f1"),
        ("a3", "e1"),
        ("b1", "g2"),
        ("b2", "f2"),
        ("b3", "e2"),

        ("e7", "a5"),
    ],
    BoardSize(8): [
        ("a1", "h1"),
        ("a2", "g1"),
        ("a3", "f1"),
        ("b1", "h2"),
        ("b2", "g2"),
        ("b3", "f2"),
    ],
}


# Simple moves in all direction, a throw and Cap/Wall placements
# Flat placements are already covered with `location_rotations`
move_rotations: dict[int, list[tuple[str, str]]] = {
    BoardSize(6): [
        ("a1>", "f1+"),
        ("a2+", "e1<"),
        ("b1<", "f2-"),
        ("b2-", "e2>"),
        ("3b5>21", "3b2+21"),
        ("Ca2", "Ce1"),
        ("Sa2", "Se1"),
        ("a2", "e1"),
    ],
    BoardSize(7): [
        ("a1>", "g1+"),
        ("a1+", "g1<"),
        ("a2<", "f1-"),
        ("a3-", "e1>"),
        ("3b5>21", "3c2+21"),
        ("Ca2", "Cf1"),
        ("Sa2", "Sf1"),
        ("a2", "f1"),
    ],
    BoardSize(8): [
        ("a1>", "h1+"),
        ("a2+", "g1<"),
        ("a3<", "f1-"),
        ("b1-", "h2>"),
        ("3b5>21", "3d2+21"),
        ("Ca2", "Cg1"),
        ("Sa2", "Sg1"),
        ("a2", "g1"),
    ],
}

rotlocs_with_size = [(size, location, expected) for [size, items] in location_rotations.items() for [location, expected] in items]
rotmoves_with_size = [(size, move, expected) for [size, items] in move_rotations.items() for [move, expected] in items]

class TestRotateMove():
    @pytest.mark.parametrize(("size", "move", "expected"), rotlocs_with_size)
    def test_rotate_placement(self, size: BoardSize, move: str, expected: str):
        assert symnorm.rotate_move(move, size) == expected


    @pytest.mark.parametrize(("size", "move", "expected"), rotmoves_with_size)
    def test_rotate_move(self, size: BoardSize, move: str, expected: str):
        assert symnorm.rotate_move(move, size) == expected


class TestRotateLocation():
    @pytest.mark.parametrize(("size", "location", "expected"), rotlocs_with_size)
    def test_rot_loc(self, size: BoardSize, location: str, expected: str):
        assert symnorm.rot_loc(location, size) == expected


class TestTransformMove():
    def test_transform_move_6s(self):
        size = BoardSize(6)
        # cennter
        expected = [
            "a1", "f1", "f6", "a6", # rotated by 0, 90, 180, 270 deg
            "a6", "a1", "f1", "f6", # flipped and then rotated by the obove
        ]
        actual = [symnorm.transform_move(expected[0], TpsSymmetry(i), size) for i in range(len(expected))]
        assert actual == expected
        # off-center
        expected = [
            "a2", "e1", "f5", "b6", # rotated by 0, 90, 180, 270 deg
            "a5", "b1", "f2", "e6", # flipped and then rotated by the obove
        ]
        actual = [symnorm.transform_move(expected[0], TpsSymmetry(i), size) for i in range(len(expected))]
        assert actual == expected

    def test_transform_move_7s(self):
        size = BoardSize(7)
        # cennter
        expected = [
            "a1", "g1", "g7", "a7", # rotated by 0, 90, 180, 270 deg
            "a7", "a1", "g1", "g7", # flipped and then rotated by the obove
        ]
        actual = [symnorm.transform_move(expected[0], TpsSymmetry(i), size) for i in range(len(expected))]
        assert actual == expected
        # off-center
        expected = [
            "a2", "f1", "g6", "b7", # rotated by 0, 90, 180, 270 deg
            "a6", "b1", "g2", "f7", # flipped and then rotated by the obove
        ]
        actual = [symnorm.transform_move(expected[0], TpsSymmetry(i), size) for i in range(len(expected))]
        assert actual == expected
