"""关卡数据。

每关是一个 Level，grid 用等长字符串表示棋盘：
    U / D / L / R -> 上 / 下 / 左 / 右 箭头
    .             -> 空格子

所有关卡都必须保证「存在合理的通关顺序」，由 test_levels.py 自动校验。
"""

from core import Level

LEVELS = [
    Level(
        name="第 1 关",
        mistakes=5,
        grid=[
            "..U..",
            ".....",
            ".U.R.",
            ".....",
            "RR..D",
        ],
    ),
    Level(
        name="第 2 关",
        mistakes=4,
        grid=[
            ".R..U",
            "..U..",
            ".....",
            "D....",
            "R.R.D",
        ],
    ),
    Level(
        name="第 3 关",
        mistakes=4,
        grid=[
            "U.D.U",
            ".....",
            "D...R",
            ".....",
            "RR.UD",
        ],
    ),
    Level(
        name="第 4 关",
        mistakes=3,
        grid=[
            ".RU.U.",
            "......",
            "U..R..",
            "...U..",
            "R.R..D",
            "......",
        ],
    ),
]
