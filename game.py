"""游戏会话层：管理关卡推进、失误次数与点击处理。

这一层也不依赖图形界面，方便对「通关 / 失败 / 重新开始」等
流程逻辑进行自动化测试（见 test_game.py）。
"""

from dataclasses import dataclass
from typing import List

from core import Board, Level


@dataclass
class ClickResult:
    """一次点击的结果，界面据此播放动画 / 更新状态。"""

    type: str          # empty / fly / collision / level_clear / all_clear / failed
    r: int = -1
    c: int = -1
    direction: str = ""   # 被点击箭头的方向（fly / collision 时有意义）
    mistakes_left: int = 0
    remaining: int = 0


class GameSession:
    """一局游戏：负责关卡列表、当前关卡、失误次数和点击判定。"""

    def __init__(self, levels: List[Level], level_index: int = 0):
        self.levels = levels
        self.level_index = level_index
        self.board: Board = Board(levels[level_index].grid)
        self.mistakes_left: int = levels[level_index].mistakes
        self.status: str = "playing"  # playing / level_clear / all_clear / failed

    @property
    def level(self) -> Level:
        return self.levels[self.level_index]

    def reset_level(self) -> None:
        """把当前关卡恢复到初始状态（重新开始）。"""
        self.board = Board(self.level.grid)
        self.mistakes_left = self.level.mistakes
        self.status = "playing"

    def next_level(self) -> None:
        self.level_index += 1
        self.reset_level()

    def click(self, r: int, c: int) -> ClickResult:
        """处理点击 (r, c)。返回一个 ClickResult 描述结果。"""
        if self.status != "playing":
            return ClickResult(
                type="empty", r=r, c=c,
                mistakes_left=self.mistakes_left,
                remaining=self.board.remaining(),
            )

        if not self.board.is_arrow(r, c):
            return ClickResult(
                type="empty", r=r, c=c,
                mistakes_left=self.mistakes_left,
                remaining=self.board.remaining(),
            )

        direction = self.board.get(r, c)

        # 前方无阻挡 -> 飞出并消除
        if self.board.path_clear(r, c):
            self.board.remove_arrow(r, c)
            remaining = self.board.remaining()
            if remaining == 0:
                if self.level_index == len(self.levels) - 1:
                    self.status = "all_clear"
                    return ClickResult(
                        type="all_clear", r=r, c=c, direction=direction,
                        mistakes_left=self.mistakes_left, remaining=0,
                    )
                self.status = "level_clear"
                return ClickResult(
                    type="level_clear", r=r, c=c, direction=direction,
                    mistakes_left=self.mistakes_left, remaining=0,
                )
            return ClickResult(
                type="fly", r=r, c=c, direction=direction,
                mistakes_left=self.mistakes_left, remaining=remaining,
            )

        # 前方有阻挡 -> 碰撞，消耗一次失误机会
        self.mistakes_left -= 1
        if self.mistakes_left <= 0:
            self.status = "failed"
            return ClickResult(
                type="failed", r=r, c=c, direction=direction,
                mistakes_left=0, remaining=self.board.remaining(),
            )
        return ClickResult(
            type="collision", r=r, c=c, direction=direction,
            mistakes_left=self.mistakes_left,
            remaining=self.board.remaining(),
        )
