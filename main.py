"""“一箭又一箭”小游戏 —— 图形界面入口。

运行方式：
    python main.py

依赖：pygame-ce（pip install pygame-ce；也可安装 pygame，二者导入名相同）。
"""

import math

import pygame

from core import DIRECTIONS, DIR_NAMES
from game import GameSession, ClickResult
from levels import LEVELS

# ---------------------------------------------------------------------------
# 基本常量
# ---------------------------------------------------------------------------
WINDOW_W = 640
WINDOW_H = 720
FPS = 60

# 配色（深色主题）
BG = (24, 26, 36)
HUD_BG = (34, 37, 52)
CELL_BG = (44, 47, 64)
CELL_BORDER = (70, 74, 96)
CELL_HOVER = (80, 86, 116)
ARROW_COLOR = (255, 178, 64)      # 橙色箭头
ARROW_BLOCKED = (255, 90, 90)     # 碰撞时变红
TEXT = (238, 240, 248)
TEXT_DIM = (160, 165, 185)
ACCENT = (255, 178, 64)
GREEN = (90, 200, 120)
RED = (255, 90, 90)
BTN_BG = (255, 178, 64)
BTN_TEXT = (30, 30, 40)
BTN_HOVER = (255, 205, 110)


# ---------------------------------------------------------------------------
# 字体与按钮辅助
# ---------------------------------------------------------------------------
def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    """加载支持中文的字体，找不到时回退到默认字体。"""
    for name in ("microsoftyahei", "msyh", "simhei", "dengxian", "simsun"):
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


class Button:
    def __init__(self, rect, text, action):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.action = action


def draw_button(screen, font, btn: Button, hover: bool):
    color = BTN_HOVER if hover else BTN_BG
    pygame.draw.rect(screen, color, btn.rect, border_radius=10)
    label = font.render(btn.text, True, BTN_TEXT)
    screen.blit(label, label.get_rect(center=btn.rect.center))


def button_at(buttons, pos):
    for b in buttons:
        if b.rect.collidepoint(pos):
            return b
    return None


# ---------------------------------------------------------------------------
# 动画对象
# ---------------------------------------------------------------------------
class FlyingArrow:
    """飞出动画：从格子中心沿方向飞到棋盘外。"""

    def __init__(self, r, c, direction, px, py, dist, cell):
        self.r, self.c = r, c
        self.direction = direction
        self.px, self.py = px, py   # 起始中心像素
        self.dist = dist            # 飞出的像素距离
        self.cell = cell
        self.progress = 0.0

    def update(self, dt):
        self.progress += dt * 2.4   # 约 0.4 秒飞完

    def done(self):
        return self.progress >= 1.0

    def draw(self, screen, size):
        dr, dc = DIRECTIONS[self.direction]
        x = self.px + dc * self.dist * self.progress
        y = self.py + dr * self.dist * self.progress
        draw_arrow(screen, x, y, self.direction, size, ARROW_COLOR)


class ShakeEffect:
    """碰撞动画：箭头向前一顶再弹回，同时变红。"""

    def __init__(self, r, c, direction, cell):
        self.r, self.c = r, c
        self.direction = direction
        self.cell = cell
        self.elapsed = 0.0
        self.duration = 0.45

    def update(self, dt):
        self.elapsed += dt

    def done(self):
        return self.elapsed >= self.duration

    def offset(self):
        """返回沿箭头方向的正向位移（像素），前半程前顶、后半程弹回。"""
        t = self.elapsed / self.duration
        return math.sin(math.pi * t) * self.cell * 0.32

    def active_color(self):
        t = self.elapsed / self.duration
        # 中间时刻最红，两端接近原色
        k = math.sin(math.pi * t)
        return lerp_color(ARROW_COLOR, ARROW_BLOCKED, k)


def lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ---------------------------------------------------------------------------
# 箭头绘制
# ---------------------------------------------------------------------------
def arrow_points(direction, size):
    """返回以 (0,0) 为中心、指向 direction、总长 size 的箭头多边形顶点。"""
    L = size
    head = L * 0.42
    half = L * 0.34
    t = L * 0.22
    # 指向“右”的基准形状（含箭杆与箭头）
    base = [
        (-L / 2, -t),
        (L / 2 - head, -t),
        (L / 2 - head, -half),
        (L / 2, 0),
        (L / 2 - head, half),
        (L / 2 - head, t),
        (-L / 2, t),
    ]
    if direction == "R":
        return base
    if direction == "L":
        return [(-x, y) for x, y in base]
    if direction == "U":
        return [(y, -x) for x, y in base]
    if direction == "D":
        return [(-y, x) for x, y in base]
    return base


def draw_arrow(screen, cx, cy, direction, size, color):
    pts = [(cx + x, cy + y) for x, y in arrow_points(direction, size)]
    pygame.draw.polygon(screen, color, pts)


# ---------------------------------------------------------------------------
# 主游戏类
# ---------------------------------------------------------------------------
class ArrowGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("一箭又一箭")
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self.clock = pygame.time.Clock()

        self.font_title = load_font(52, bold=True)
        self.font_big = load_font(34, bold=True)
        self.font_mid = load_font(26, bold=True)
        self.font_body = load_font(22)
        self.font_small = load_font(18)

        self.state = "MENU"          # MENU / PLAYING / LEVEL_CLEAR / ALL_CLEAR / FAILED
        self.session = GameSession(LEVELS)
        self.flying = []             # FlyingArrow 列表
        self.shakes = []             # ShakeEffect 列表
        self.pending_state = None    # 延迟切换的状态（让动画播放完）
        self.pending_timer = 0.0

        self.layout = {}             # 棋盘布局：x0/y0/cell
        self.build_buttons()
        self.compute_layout()

    # ------------------------------ 布局与按钮 ------------------------------
    def build_buttons(self):
        self.buttons = {
            "MENU": [Button((WINDOW_W // 2 - 130, 460, 260, 62), "开始游戏", "start")],
            "PLAYING": [Button((WINDOW_W - 150, 22, 128, 46), "重新开始", "restart")],
            "LEVEL_CLEAR": [
                Button((WINDOW_W // 2 - 130, 440, 260, 62), "下一关", "next"),
                Button((WINDOW_W // 2 - 130, 522, 260, 52), "返回菜单", "menu"),
            ],
            "ALL_CLEAR": [
                Button((WINDOW_W // 2 - 130, 440, 260, 62), "再玩一次", "restart_all"),
                Button((WINDOW_W // 2 - 130, 522, 260, 52), "返回菜单", "menu"),
            ],
            "FAILED": [
                Button((WINDOW_W // 2 - 130, 440, 260, 62), "重新开始", "restart"),
                Button((WINDOW_W // 2 - 130, 522, 260, 52), "返回菜单", "menu"),
            ],
        }

    def compute_layout(self):
        """根据当前关卡的网格大小计算棋盘位置与格子边长。"""
        rows, cols = self.session.board.rows, self.session.board.cols
        area = 500
        cell = min(area // cols, area // rows)
        board_w = cell * cols
        board_h = cell * rows
        x0 = (WINDOW_W - board_w) // 2
        y0 = 165 + (area - board_h) // 2
        self.layout = {"x0": x0, "y0": y0, "cell": cell}

    def cell_center(self, r, c):
        cell = self.layout["cell"]
        return (self.layout["x0"] + c * cell + cell / 2,
                self.layout["y0"] + r * cell + cell / 2)

    def pixel_to_cell(self, pos):
        x0, y0, cell = self.layout["x0"], self.layout["y0"], self.layout["cell"]
        c = int((pos[0] - x0) // cell)
        r = int((pos[1] - y0) // cell)
        if 0 <= r < self.session.board.rows and 0 <= c < self.session.board.cols:
            return r, c
        return None

    # ------------------------------ 游戏流程 ------------------------------
    def start_game(self):
        self.session = GameSession(LEVELS)
        self.flying = []
        self.shakes = []
        self.pending_state = None
        self.compute_layout()
        self.state = "PLAYING"

    def restart_level(self):
        self.session.reset_level()
        self.flying = []
        self.shakes = []
        self.pending_state = None
        self.state = "PLAYING"

    def handle_board_click(self, r, c):
        res = self.session.click(r, c)
        if res.type == "empty":
            return

        if res.type in ("fly", "level_clear", "all_clear"):
            px, py = self.cell_center(r, c)
            dr, dc = DIRECTIONS[res.direction]
            # 计算飞到棋盘外的距离
            rows, cols = self.session.board.rows, self.session.board.cols
            if res.direction == "R":
                steps = cols - 1 - c
            elif res.direction == "L":
                steps = c
            elif res.direction == "D":
                steps = rows - 1 - r
            else:
                steps = r
            dist = (steps + 1.4) * self.layout["cell"]
            self.flying.append(FlyingArrow(r, c, res.direction, px, py, dist,
                                           self.layout["cell"]))
            if res.type == "level_clear":
                self.schedule("LEVEL_CLEAR", 0.8)
            elif res.type == "all_clear":
                self.schedule("ALL_CLEAR", 0.8)

        elif res.type in ("collision", "failed"):
            self.shakes.append(
                ShakeEffect(r, c, res.direction, self.layout["cell"])
            )
            if res.type == "failed":
                self.schedule("FAILED", 0.9)

    def schedule(self, state, delay):
        self.pending_state = state
        self.pending_timer = delay

    # ------------------------------ 主循环 ------------------------------
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            running = self.handle_events()
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.on_click(mouse_pos)
        return True

    def on_click(self, pos):
        btn = button_at(self.buttons.get(self.state, []), pos)
        if btn:
            self.handle_button(btn.action)
            return

        if self.state == "PLAYING" and self.pending_state is None:
            cell = self.pixel_to_cell(pos)
            if cell:
                self.handle_board_click(*cell)

    def handle_button(self, action):
        if action == "start":
            self.start_game()
        elif action == "restart":
            self.restart_level()
        elif action == "restart_all":
            self.start_game()
        elif action == "next":
            self.session.next_level()
            self.flying = []
            self.shakes = []
            self.compute_layout()
            self.state = "PLAYING"
        elif action == "menu":
            self.session = GameSession(LEVELS)
            self.flying = []
            self.shakes = []
            self.pending_state = None
            self.compute_layout()
            self.state = "MENU"

    def update(self, dt):
        for f in self.flying:
            f.update(dt)
        self.flying = [f for f in self.flying if not f.done()]
        for s in self.shakes:
            s.update(dt)
        self.shakes = [s for s in self.shakes if not s.done()]

        if self.pending_state:
            self.pending_timer -= dt
            if self.pending_timer <= 0:
                self.state = self.pending_state
                self.pending_state = None

    # ------------------------------ 绘制 ------------------------------
    def draw(self):
        self.screen.fill(BG)
        if self.state == "MENU":
            self.draw_menu()
        else:
            self.draw_board()
            self.draw_hud()
            for f in self.flying:
                f.draw(self.screen, self.layout["cell"] * 0.6)
            if self.state == "LEVEL_CLEAR":
                self.draw_overlay("通关！", f"{self.session.level.name} 完成",
                                  "下一关", GREEN)
            elif self.state == "ALL_CLEAR":
                self.draw_overlay("恭喜！", "全部关卡通关！", None, GREEN)
            elif self.state == "FAILED":
                self.draw_overlay("失败", "失误次数已用尽", "重新开始", RED)

    def draw_menu(self):
        title = self.font_title.render("一箭又一箭", True, ACCENT)
        self.screen.blit(title, title.get_rect(center=(WINDOW_W // 2, 200)))

        subtitle = self.font_body.render("点击箭头，让所有箭头飞出棋盘", True, TEXT)
        self.screen.blit(subtitle, subtitle.get_rect(center=(WINDOW_W // 2, 270)))

        lines = [
            "· 箭头朝哪个方向，就朝哪个方向飞",
            "· 前方无阻挡的箭头点击后飞出并消失",
            "· 前方有箭头的会被挡住，并消耗一次失误机会",
            "· 消除全部箭头即可通关",
        ]
        for i, line in enumerate(lines):
            txt = self.font_small.render(line, True, TEXT_DIM)
            self.screen.blit(txt, txt.get_rect(center=(WINDOW_W // 2, 330 + i * 28)))

        hint = self.font_small.render(f"共 {len(LEVELS)} 关", True, TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(WINDOW_W // 2, 560)))

        self.draw_state_buttons()

    def draw_hud(self):
        # 顶部信息条背景
        pygame.draw.rect(self.screen, HUD_BG, (0, 0, WINDOW_W, 150))

        name = self.font_mid.render(self.session.level.name, True, TEXT)
        self.screen.blit(name, (24, 20))

        arrow_txt = self.font_body.render(
            f"剩余箭头：{self.session.board.remaining()}", True, TEXT)
        self.screen.blit(arrow_txt, (24, 66))

        # 剩余失误次数：耗尽时用红色强调
        mcolor = RED if self.session.mistakes_left <= 1 else TEXT
        mistake_txt = self.font_body.render(
            f"剩余失误：{self.session.mistakes_left}", True, mcolor)
        self.screen.blit(mistake_txt, (24, 102))

        self.draw_state_buttons()

    def draw_board(self):
        board = self.session.board
        cell = self.layout["cell"]
        x0, y0 = self.layout["x0"], self.layout["y0"]
        mouse = pygame.mouse.get_pos()
        hover_cell = self.pixel_to_cell(mouse) if self.state == "PLAYING" else None

        for r in range(board.rows):
            for c in range(board.cols):
                rect = pygame.Rect(x0 + c * cell, y0 + r * cell, cell, cell)
                color = CELL_HOVER if (r, c) == hover_cell and board.is_arrow(r, c) else CELL_BG
                pygame.draw.rect(self.screen, color, rect, border_radius=6)
                pygame.draw.rect(self.screen, CELL_BORDER, rect, width=2, border_radius=6)

        for (r, c), d in self._iter_arrows():
            cx, cy = self.cell_center(r, c)
            shake = self._shake_at(r, c)
            if shake:
                dr, dc = DIRECTIONS[d]
                off = shake.offset()
                cx += dc * off
                cy += dr * off
                color = shake.active_color()
            else:
                color = ARROW_COLOR
            draw_arrow(self.screen, cx, cy, d, cell * 0.62, color)

    def _iter_arrows(self):
        board = self.session.board
        for r in range(board.rows):
            for c in range(board.cols):
                d = board.get(r, c)
                if d in DIRECTIONS:
                    yield (r, c), d

    def _shake_at(self, r, c):
        for s in self.shakes:
            if s.r == r and s.c == c:
                return s
        return None

    def draw_overlay(self, title, subtitle, btn_label, color):
        # 半透明遮罩
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill((15, 17, 26, 185))
        self.screen.blit(overlay, (0, 0))

        t = self.font_big.render(title, True, color)
        self.screen.blit(t, t.get_rect(center=(WINDOW_W // 2, 300)))
        s = self.font_body.render(subtitle, True, TEXT)
        self.screen.blit(s, s.get_rect(center=(WINDOW_W // 2, 360)))

        self.draw_state_buttons()

    def draw_state_buttons(self):
        mouse = pygame.mouse.get_pos()
        for b in self.buttons.get(self.state, []):
            draw_button(self.screen, self.font_mid, b, b.rect.collidepoint(mouse))


def main():
    ArrowGame().run()


if __name__ == "__main__":
    main()
