import pytest
from base_types import BoardSize
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

rotlocs_with_size = [(size, move, expected) for [size, items] in location_rotations.items() for [move, expected] in items]

class TestRotateMove():
    @pytest.mark.parametrize(("size", "move", "expected"), rotlocs_with_size)
    def test_rotate_placement(self, size: BoardSize, move: str, expected: str):
        assert symnorm.rotate_move(move, size) == expected

    # todo test throw-moves, capstone and wall placements

class TestRotLoc():
    @pytest.mark.parametrize(("size", "location", "expected"), rotlocs_with_size)
    def test_rot_loc(self, size: BoardSize, location: str, expected: str):
        assert symnorm.rot_loc(location, size) == expected


