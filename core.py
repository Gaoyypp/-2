"""“一箭又一箭”核心游戏逻辑。

本模块只包含与图形界面无关的纯逻辑，方便单独测试：
- 棋盘（网格）的表示
- 箭头方向与路径检测
- 箭头消除 / 碰撞判断
- 关卡是否可通关的自动求解

棋盘用一个二维字符网格表示，每个格子：
    'U' / 'D' / 'L' / 'R'  -> 上 / 下 / 左 / 右 四种箭头
    '.'                    -> 空格子
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

# 四个方向的坐标增量：(行增量, 列增量)
# 屏幕坐标里“上”是行号减小（row - 1）
DIRECTIONS = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}

# 方向的中文名，供界面 / 提示使用
DIR_NAMES = {"U": "上", "D": "下", "L": "左", "R": "右"}


@dataclass
class Level:
    """一个关卡。grid 是若干等长字符串组成的棋盘。"""

    name: str
    grid: List[str]
    mistakes: int = 3  # 本关允许的失误次数

    def rows(self) -> int:
        return len(self.grid)

    def cols(self) -> int:
        return len(self.grid[0]) if self.grid else 0


class Board:
    """可变的棋盘状态，支持检测、消除与求解。"""

    def __init__(self, grid: List[str]):
        # 复制成 list[list[str]]，避免外部修改
        self.grid = [list(row) for row in grid]
        self.rows = len(self.grid)
        self.cols = len(self.grid[0]) if self.rows else 0

    def get(self, r: int, c: int) -> str:
        """返回 (r, c) 处的字符；越界返回 '.'。"""
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self.grid[r][c]
        return "."

    def is_arrow(self, r: int, c: int) -> bool:
        return self.get(r, c) in DIRECTIONS

    def path_clear(self, r: int, c: int) -> bool:
        """判断 (r, c) 处箭头前进方向到边界之间是否没有其他箭头。

        沿箭头方向逐格前进，直到走出棋盘：
        - 若中途遇到任何箭头（不是 '.'），说明被阻挡，返回 False；
        - 若能一直走到棋盘外，说明前方无阻挡，返回 True。
        """
        d = self.get(r, c)
        if d not in DIRECTIONS:
            return False
        dr, dc = DIRECTIONS[d]
        nr, nc = r + dr, c + dc
        while 0 <= nr < self.rows and 0 <= nc < self.cols:
            if self.grid[nr][nc] != ".":
                return False
            nr += dr
            nc += dc
        return True

    def remove_arrow(self, r: int, c: int) -> None:
        """把 (r, c) 处的箭头清除（飞出棋盘）。"""
        self.grid[r][c] = "."

    def remaining(self) -> int:
        """剩余箭头数量。"""
        return sum(1 for row in self.grid for ch in row if ch in DIRECTIONS)

    def all_arrows(self) -> List[Tuple[int, int]]:
        """返回所有箭头的坐标列表。"""
        return [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if self.grid[r][c] in DIRECTIONS
        ]

    def clearable_arrows(self) -> List[Tuple[int, int]]:
        """当前所有「前方无阻挡」可飞出的箭头坐标。"""
        return [(r, c) for (r, c) in self.all_arrows() if self.path_clear(r, c)]

    def solved(self) -> bool:
        return self.remaining() == 0

    def solve(self) -> Optional[List[Tuple[int, int]]]:
        """自动求解：贪心地反复消除任意「前方无阻挡」的箭头。

        关键性质：消除一个箭头只会减少障碍、不会新增障碍，
        因此「当前可消除箭头集合」随消除单调递增，贪心选择不会选错。
        若能全部消除，返回一个可行的消除顺序；否则返回 None（关卡死锁）。
        """
        work = Board(self.grid)
        order: List[Tuple[int, int]] = []
        while not work.solved():
            candidates = work.clearable_arrows()
            if not candidates:
                return None  # 还有箭头却一个也动不了 -> 无法通关
            r, c = candidates[0]
            work.remove_arrow(r, c)
            order.append((r, c))
        return order

    def is_solvable(self) -> bool:
        return self.solve() is not None
