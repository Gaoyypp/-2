"""自动化测试：覆盖作业要求的 T01 ~ T06，并校验所有关卡可通关。

运行：
    python -m unittest test_game -v
"""

import unittest

from core import Board, DIRECTIONS
from game import GameSession
from levels import LEVELS


class TestPathDetection(unittest.TestCase):
    """T01 / T02 / T03：路径检测与越界处理。"""

    def test_T01_clear_arrow_flys(self):
        """前方无阻挡的箭头可以飞出并消失。"""
        b = Board(["R..", "..."])  # (0,0) 朝右，右侧无阻挡
        self.assertTrue(b.path_clear(0, 0))
        b.remove_arrow(0, 0)
        self.assertFalse(b.is_arrow(0, 0))
        self.assertEqual(b.remaining(), 0)

    def test_T02_blocked_arrow_not_removed(self):
        """前方有阻挡的箭头不能飞出。"""
        b = Board(["R.R"])  # (0,0) 朝右，被 (0,2) 挡住
        self.assertFalse(b.path_clear(0, 0))
        # 用会话验证失误次数减 1
        s = GameSession([_level(["R.R"], mistakes=3)])
        res = s.click(0, 0)
        self.assertEqual(res.type, "collision")
        self.assertEqual(res.mistakes_left, 2)
        self.assertTrue(s.board.is_arrow(0, 0))  # 箭头仍在

    def test_T03_edge_arrows_no_error(self):
        """边缘且朝外的箭头正常消失，不发生越界。"""
        cases = [
            (["R.."], (0, 0)),   # 左边缘朝右
            (["..R"], (0, 2)),   # 右边缘朝右
            (["U", ".", "."], (0, 0)),   # 上边缘朝上
            ([".", ".", "D"], (2, 0)),   # 下边缘朝下
        ]
        for grid, (r, c) in cases:
            b = Board(grid)
            self.assertTrue(b.path_clear(r, c), f"{grid} {r},{c}")
            b.remove_arrow(r, c)
            self.assertFalse(b.is_arrow(r, c))


class TestGameFlow(unittest.TestCase):
    """T04 / T05 / T06：通关、失败、重新开始流程。"""

    def test_T04_clear_all_arrows(self):
        """消除全部箭头后进入下一关。"""
        s = GameSession(LEVELS)
        for lv in LEVELS:
            self.assertEqual(s.status, "playing", lv.name)
            for r, c in s.board.solve():
                res = s.click(r, c)
                if s.board.remaining() == 0:
                    self.assertIn(res.type, ("level_clear", "all_clear"))
            if s.level_index < len(LEVELS) - 1:
                s.next_level()
        self.assertEqual(s.status, "all_clear")

    def test_T05_mistakes_exhausted(self):
        """失误次数耗尽后失败。"""
        s = GameSession([_level(["R.R"], mistakes=1)])
        self.assertEqual(s.status, "playing")
        res = s.click(0, 0)   # 被阻挡，失误 -1
        self.assertEqual(res.type, "failed")
        self.assertEqual(s.status, "failed")
        self.assertEqual(s.mistakes_left, 0)

    def test_T06_restart_resets(self):
        """游戏进行中重新开始，布局与失误次数恢复。"""
        s = GameSession([_level(["R.R"], mistakes=3)])
        s.click(0, 0)  # 碰撞，失误 -1
        self.assertEqual(s.mistakes_left, 2)
        s.click(0, 2)  # 飞出
        self.assertEqual(s.board.remaining(), 1)
        s.reset_level()
        self.assertEqual(s.mistakes_left, 3)
        self.assertEqual(s.board.remaining(), 2)
        self.assertTrue(s.board.is_arrow(0, 0) and s.board.is_arrow(0, 2))


class TestLevels(unittest.TestCase):
    """所有关卡都必须存在合理通关顺序。"""

    def test_all_levels_solvable(self):
        self.assertGreaterEqual(len(LEVELS), 3)
        for lv in LEVELS:
            b = Board(lv.grid)
            self.assertIsNotNone(b.solve(), f"{lv.name} 无法通关")
            # 每个格子字符必须合法
            for row in lv.grid:
                for ch in row:
                    self.assertIn(ch, DIRECTIONS.keys() | {"."})

    def test_solve_actually_clears(self):
        for lv in LEVELS:
            b = Board(lv.grid)
            order = b.solve()
            for r, c in order:
                self.assertTrue(b.path_clear(r, c), f"{lv.name} 顺序非法")
                b.remove_arrow(r, c)
            self.assertTrue(b.solved(), lv.name)


def _level(grid, mistakes):
    from core import Level
    return Level("test", grid, mistakes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
