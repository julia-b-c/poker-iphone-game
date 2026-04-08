import asyncio
import pygame
import random
import sys
import time
from collections import Counter


# --- 1. Configuration & Initialization ---
pygame.init()

WIDTH, HEIGHT = 1200, 800
screen = pygame.Surface((WIDTH, HEIGHT))
window = None
render_rect = pygame.Rect(0, 0, WIDTH, HEIGHT)
pygame.display.set_caption("Texas Hold'em - 8 Player Ring Game - iPhone Web")

# --- WSOP Color Palette ---
WSOP_BLUE = (20, 30, 60)
WSOP_BORDER = (200, 160, 50)
WSOP_ACCENT = (212, 175, 55)
FELT_LINE = (50, 60, 90)

# Standard Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 20, 60)
YELLOW = (255, 255, 0)
GRAY = (50, 50, 50)
DISABLED_GRAY = (100, 100, 100)
INPUT_BG = (240, 240, 240)
INPUT_ACTIVE = (255, 255, 255)
TIMER_RED = (255, 69, 0)

# Button Colors
BLUE_BTN = (40, 60, 120)
BLUE_BTN_HOVER = (60, 80, 160)
ORANGE_BTN = (200, 100, 0)
ORANGE_BTN_HOVER = (230, 130, 20)
RED_BTN = (160, 30, 30)
RED_BTN_HOVER = (200, 50, 50)
GOLD_BTN = (180, 140, 20)

# Indicators
ORANGE_MARKER = (255, 140, 0)
PURPLE_SB = (147, 112, 219)
BLUE_BB = (65, 105, 225)

# Fonts
font_huge = pygame.font.SysFont("impact", 80)
font_large = pygame.font.SysFont("arial", 40, bold=True)
font_bet_amount = pygame.font.SysFont("impact", 28) 
font_med = pygame.font.SysFont("arial", 22, bold=True)
font_small = pygame.font.SysFont("arial", 16, bold=True)
font_tiny = pygame.font.SysFont("arial", 14, bold=True)
font_timer = pygame.font.SysFont("arial", 20, bold=True)
font_win = pygame.font.SysFont("arial", 26, bold=True)

# Suit Font
font_suit = pygame.font.SysFont("segoeuisymbol", 40)
if font_suit.get_height() < 20:
    font_suit = pygame.font.SysFont("arial", 40)

# Game Parameters
CARD_WIDTH, CARD_HEIGHT = 60, 90
INITIAL_STACK = 100000
SMALL_BLIND = 100
BIG_BLIND = 200
TURN_TIME_LIMIT = 30
BOT_ACTION_DELAY_MS = 900

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUES = {r: i for i, r in enumerate(RANKS, 2)}


def clamp(value, low, high):
    return max(low, min(high, value))


def refresh_window(size=None):
    global window, render_rect

    flags = pygame.RESIZABLE
    if window is None:
        window = pygame.display.set_mode(size or (WIDTH, HEIGHT), flags)
    elif size is not None:
        window = pygame.display.set_mode(size, flags)

    win_w, win_h = window.get_size()
    scale = min(win_w / WIDTH, win_h / HEIGHT)
    draw_w = max(1, int(WIDTH * scale))
    draw_h = max(1, int(HEIGHT * scale))
    render_rect = pygame.Rect((win_w - draw_w) // 2, (win_h - draw_h) // 2, draw_w, draw_h)


def to_virtual_pos(pos):
    if render_rect.width <= 0 or render_rect.height <= 0:
        return 0, 0

    rel_x = (pos[0] - render_rect.x) / render_rect.width
    rel_y = (pos[1] - render_rect.y) / render_rect.height
    x = int(clamp(rel_x * WIDTH, 0, WIDTH - 1))
    y = int(clamp(rel_y * HEIGHT, 0, HEIGHT - 1))
    return x, y


def get_pointer_pos():
    return to_virtual_pos(pygame.mouse.get_pos())


def present_frame():
    if window is None:
        refresh_window()

    window.fill((0, 0, 0))
    frame = pygame.transform.smoothscale(screen, render_rect.size)
    window.blit(frame, render_rect.topleft)
    pygame.display.flip()


def compare_hand_values(a, b):
    left = (a[0], a[1])
    right = (b[0], b[1])
    if left > right:
        return 1
    if left < right:
        return -1
    return 0


def preflop_hand_strength(card_a, card_b):
    v1, v2 = sorted([card_a.value, card_b.value], reverse=True)
    suited = card_a.suit == card_b.suit
    pair = v1 == v2
    gap = v1 - v2

    if pair:
        score = 0.40 + (v1 / 14) * 0.42
        if v1 >= 10:
            score += 0.08
        elif v1 <= 4:
            score -= 0.03
    else:
        score = 0.10 + (v1 / 14) * 0.25 + (v2 / 14) * 0.15
        if suited:
            score += 0.06
        if gap == 1:
            score += 0.07
        elif gap == 2:
            score += 0.04
        elif gap == 3:
            score += 0.02
        elif gap > 4:
            score -= 0.05

        if v1 == 14 and v2 >= 10:
            score += 0.12
        elif v1 >= 13 and v2 >= 10:
            score += 0.08
        elif v1 >= 12 and v2 >= 10:
            score += 0.05

        if v1 >= 10 and v2 >= 10:
            score += 0.05
        if v2 <= 4 and gap > 5:
            score -= 0.04

    return clamp(score, 0.05, 0.97)


def get_straight_draw_info(values):
    uniq = sorted(set(values))
    if 14 in uniq:
        uniq = [1] + uniq

    uniq_set = set(uniq)
    open_ended = False
    gutshot = False

    for start in range(1, 11):
        needed = set(range(start, start + 5))
        have = needed & uniq_set
        if len(have) != 4:
            continue
        missing = list(needed - have)[0]
        if missing == start or missing == start + 4:
            open_ended = True
        else:
            gutshot = True

    return open_ended, gutshot


def estimate_equity(hero_cards, community_cards, num_opponents, simulations=180):
    if num_opponents <= 0:
        return 1.0

    known = {(c.suit, c.rank) for c in hero_cards + community_cards}
    remaining = [Card(s, r) for s in SUITS for r in RANKS if (s, r) not in known]
    board_to_draw = 5 - len(community_cards)
    total_needed = board_to_draw + num_opponents * 2
    if total_needed <= 0:
        total_needed = num_opponents * 2
    if total_needed > len(remaining):
        return 0.0

    sims = max(60, simulations)
    total = 0.0

    for _ in range(sims):
        sampled = random.sample(remaining, total_needed)
        future_board = community_cards + sampled[:board_to_draw]
        cursor = board_to_draw

        hero_value = evaluate_hand(hero_cards + future_board)
        hero_is_best = True
        tied_players = 1

        for _opp in range(num_opponents):
            opp_cards = sampled[cursor:cursor + 2]
            cursor += 2
            opp_value = evaluate_hand(opp_cards + future_board)
            comp = compare_hand_values(opp_value, hero_value)
            if comp > 0:
                hero_is_best = False
                break
            if comp == 0:
                tied_players += 1

        if hero_is_best:
            total += 1.0 / tied_players

    return total / sims

# --- Bot Profiles (Expanded to 7 bots for 8-max table) ---
BOT_PROFILES = [
    {"name": "Eltonzeng", "style": "Loose Aggro", "aggr": 0.85, "loose": 0.80, "bluff": 0.70}, # New
    {"name": "andy",      "style": "Tight Rock",  "aggr": 0.30, "loose": 0.20, "bluff": 0.10}, # New
    {"name": "Tan Xuan",  "style": "Maniac",      "aggr": 0.95, "loose": 0.90, "bluff": 0.80},
    {"name": "Rui Cao",   "style": "Balanced",    "aggr": 0.65, "loose": 0.50, "bluff": 0.40},
    {"name": "Tom Dwan",  "style": "Tricky",      "aggr": 0.80, "loose": 0.70, "bluff": 0.70},
    {"name": "Phil Ivey", "style": "The GOAT",    "aggr": 0.70, "loose": 0.40, "bluff": 0.50},
    {"name": "Jungleman", "style": "GTO Math",    "aggr": 0.50, "loose": 0.30, "bluff": 0.20},
]

# --- 2. Hand Evaluation Logic ---
def evaluate_hand(cards):
    if not cards: return (0, [], "")
    values = sorted([c.value for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    suit_counts = Counter(suits)
    value_counts = Counter(values)

    is_flush, flush_suit = False, None
    for s, c in suit_counts.items():
        if c >= 5: is_flush, flush_suit = True, s

    flush_cards = sorted([c.value for c in cards if c.suit == flush_suit], reverse=True) if is_flush else []

    def get_straight(vals):
        uniq = sorted(list(set(vals)), reverse=True)
        if {14, 5, 4, 3, 2}.issubset(set(uniq)): return 5
        for i in range(len(uniq) - 4):
            if uniq[i] - uniq[i+4] == 4: return uniq[i]
        return None

    straight_high = get_straight(values)

    if is_flush:
        sf_high = get_straight(flush_cards)
        if sf_high: return (8, [sf_high], "Straight Flush")

    four = [v for v, c in value_counts.items() if c == 4]
    if four:
        kicker = max([v for v in values if v != four[0]])
        return (7, [four[0], kicker], "Four of a Kind")

    three = [v for v, c in value_counts.items() if c >= 3]
    pairs = [v for v, c in value_counts.items() if c >= 2]

    if three:
        max_three = max(three)
        rem_pairs = [p for p in pairs if p != max_three]
        if rem_pairs:
            max_pair = max(rem_pairs)
            return (6, [max_three, max_pair], "Full House")

    if is_flush: return (5, flush_cards[:5], "Flush")
    if straight_high: return (4, [straight_high], "Straight")

    if three:
        max_three = max(three)
        kickers = [v for v in values if v != max_three]
        return (3, [max_three] + kickers[:2], "Three of a Kind")

    if len(pairs) >= 2:
        pairs.sort(reverse=True)
        top_two = pairs[:2]
        kicker = max([v for v in values if v not in top_two])
        return (2, top_two + [kicker], "Two Pair")

    if len(pairs) == 1:
        p_val = pairs[0]
        kickers = [v for v in values if v != p_val]
        return (1, [p_val] + kickers[:3], "Pair")

    return (0, values[:5], "High Card")

# --- 3. UI Classes ---
class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.value = RANK_VALUES[rank]
        self.is_face_up = True
        self.rect = pygame.Rect(0, 0, CARD_WIDTH, CARD_HEIGHT)

    def draw(self, surface, x, y, scale=1.0):
        w = int(CARD_WIDTH * scale)
        h = int(CARD_HEIGHT * scale)
        self.rect = pygame.Rect(x, y, w, h)

        if self.is_face_up:
            pygame.draw.rect(surface, WHITE, self.rect, border_radius=int(5*scale))
            pygame.draw.rect(surface, BLACK, self.rect, 2, border_radius=int(5*scale))
            color = RED if self.suit in ['♥', '♦'] else BLACK

            s_font_rank = pygame.font.SysFont("arial", int(32*scale), bold=True)
            s_font_suit = pygame.font.SysFont("segoeuisymbol", int(40*scale))
            if s_font_suit.get_height() < int(20*scale):
                 s_font_suit = pygame.font.SysFont("arial", int(40*scale))

            rank_txt = s_font_rank.render(self.rank, True, color)
            surface.blit(rank_txt, (x + int(4*scale), y + int(2*scale)))
            
            suit_txt = s_font_suit.render(self.suit, True, color)
            s_rect = suit_txt.get_rect(center=(x + w//2, y + h//2 + 5))
            surface.blit(suit_txt, s_rect)
        else:
            pygame.draw.rect(surface, (40, 60, 150), self.rect, border_radius=int(5*scale))
            pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=int(5*scale))
            pygame.draw.line(surface, (60, 80, 180), (x, y), (x+w, y+h), 2)
            pygame.draw.line(surface, (60, 80, 180), (x+w, y), (x, y+h), 2)

class Button:
    def __init__(self, text, x, y, w, h, color, hover_color, action_code):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.base_color = color
        self.hover_color = hover_color
        self.action_code = action_code
        self.active = True

    def draw(self, surface):
        if not self.active:
            if self.action_code == 4: return
            draw_col = DISABLED_GRAY
        else:
            mouse_pos = get_pointer_pos()
            is_hover = self.rect.collidepoint(mouse_pos)
            draw_col = self.hover_color if is_hover else self.base_color

        shadow_rect = self.rect.move(2, 2)
        pygame.draw.rect(surface, (30, 30, 30), shadow_rect, border_radius=8)
        pygame.draw.rect(surface, draw_col, self.rect, border_radius=8)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2, border_radius=8)

        txt_col = WHITE if self.active else (50, 50, 50)
        txt = font_med.render(self.text, True, txt_col)
        txt_rect = txt.get_rect(center=self.rect.center)
        surface.blit(txt, txt_rect)

    def is_clicked(self, pos):
        return self.active and self.rect.collidepoint(pos)

class InputBox:
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = INPUT_BG
        self.text = text
        self.txt_surface = font_med.render(text, True, BLACK)
        self.active = False

    def handle_event(self, event):
        if not self.active: return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                return
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                if event.unicode.isdigit():
                    self.text += event.unicode
            self.txt_surface = font_med.render(self.text, True, BLACK)

    def update(self):
        width = max(100, self.txt_surface.get_width()+10)
        self.rect.w = width

    def draw(self, screen):
        if not self.active: return
        self.color = INPUT_ACTIVE
        pygame.draw.rect(screen, self.color, self.rect, border_radius=5)
        pygame.draw.rect(screen, BLACK, self.rect, 2, border_radius=5)
        screen.blit(self.txt_surface, (self.rect.x+5, self.rect.y+10))
        label = font_small.render("Bet Amount:", True, WSOP_ACCENT)
        screen.blit(label, (self.rect.x, self.rect.y - 25))

# --- 4. Player Class ---
class Player:
    def __init__(self, name, x, y, bet_x, bet_y, is_human=False, profile=None):
        self.name = name
        self.chips = INITIAL_STACK
        self.hand = []
        self.is_human = is_human
        self.has_folded = False
        self.is_active = True
        self.is_all_in = False
        self.x = x
        self.y = y
        self.bet_x = bet_x
        self.bet_y = bet_y
        self.round_bet = 0
        self.last_action = ""
        self.acted_this_street = False
        self.win_desc = None
        self.profile = profile
        self.hand_read_strength = 0.0

    def reset_for_new_hand(self):
        self.hand = []
        self.has_folded = False
        self.round_bet = 0
        self.last_action = ""
        self.acted_this_street = False
        self.win_desc = None
        self.hand_read_strength = 0.0

        if self.chips > 0:
            self.is_active = True
            self.is_all_in = False
        else:
            self.is_active = False
            self.is_all_in = True

    def reset_for_next_street(self):
        self.round_bet = 0
        self.last_action = ""
        self.acted_this_street = False

    def bet(self, amount):
        actual = min(self.chips, amount)
        self.chips -= actual
        self.round_bet += actual
        if self.chips == 0:
            self.is_all_in = True
        return actual

# --- 5. Main Game Logic ---
class PokerGame:
    def __init__(self):
        self.players = []
        
        # --- 8-Player Coordinates ---
        # 0: You (Bottom Center)
        # 1: Eltonzeng (Bottom Left)
        # 2: andy (Left)
        # 3: Tan Xuan (Top Left)
        # 4: Rui Cao (Top Center Left)
        # 5: Tom Dwan (Top Center Right)
        # 6: Phil Ivey (Top Right)
        # 7: Jungleman (Right)
        # 8: (Wait, we need 8 players total, so 7 bots)
        
        seat_configs = [
            {"pos": (WIDTH//2 - 60, HEIGHT - 170), "bet": (WIDTH//2, HEIGHT - 240)}, # 0. You
            {"pos": (120, HEIGHT - 200),           "bet": (200, HEIGHT - 250)},      # 1. Bot (Eltonzeng)
            {"pos": (40, HEIGHT//2),               "bet": (150, HEIGHT//2)},         # 2. Bot (andy)
            {"pos": (120, 150),                    "bet": (220, 220)},               # 3. Bot (Tan Xuan)
            {"pos": (WIDTH//2 - 160, 60),          "bet": (WIDTH//2 - 100, 180)},    # 4. Bot (Rui Cao)
            {"pos": (WIDTH//2 + 60, 60),           "bet": (WIDTH//2 + 100, 180)},    # 5. Bot (Tom Dwan)
            {"pos": (WIDTH - 220, 150),            "bet": (WIDTH - 280, 220)},       # 6. Bot (Phil Ivey)
            {"pos": (WIDTH - 140, HEIGHT//2),      "bet": (WIDTH - 200, HEIGHT//2)}, # 7. Bot (Jungleman)
        ]

        self.players.append(Player("You", seat_configs[0]["pos"][0], seat_configs[0]["pos"][1], seat_configs[0]["bet"][0], seat_configs[0]["bet"][1], is_human=True))

        # Add 7 Bots
        for i in range(1, 8):
            cfg = seat_configs[i]
            # Use profiles cyclically if needed, but we have 7 profiles now
            profile = BOT_PROFILES[(i-1) % len(BOT_PROFILES)]
            self.players.append(Player(profile["name"], cfg["pos"][0], cfg["pos"][1], cfg["bet"][0], cfg["bet"][1], profile=profile))

        self.dealer_index = 0
        self.turn_index = 0
        self.turn_start_time = 0
        self.last_bot_action_time = 0

        self.deck = []
        self.community = []
        self.pot = 0
        self.stage = 0
        self.street_high_bet = 0
        self.msg = "Ready to Start!"
        self.buttons = []
        self.input_box = None
        self.top_status = "Welcome"
        self.preflop_last_raiser = None
        self.street_last_aggressor = None

        self.start_new_hand()

    def init_game_ui(self):
        btn_y = HEIGHT - 80
        self.btn_check_call = Button("Check/Call", WIDTH//2 - 300, btn_y, 160, 50, BLUE_BTN, BLUE_BTN_HOVER, 1)
        self.input_box = InputBox(WIDTH//2 - 100, btn_y, 100, 50)
        self.btn_confirm_bet = Button("Bet/Raise", WIDTH//2 + 20, btn_y, 120, 50, ORANGE_BTN, ORANGE_BTN_HOVER, 2)
        self.btn_fold = Button("Fold", WIDTH//2 + 150, btn_y, 140, 50, RED_BTN, RED_BTN_HOVER, 3)
        self.btn_next = Button("Next Hand", WIDTH//2 - 70, btn_y, 140, 50, GOLD_BTN, YELLOW, 4)
        quick_y = HEIGHT - 145
        self.quick_buttons = [
            Button("Clear", WIDTH//2 - 300, quick_y, 110, 44, GRAY, DISABLED_GRAY, 11),
            Button("Min", WIDTH//2 - 180, quick_y, 90, 44, BLUE_BTN, BLUE_BTN_HOVER, 12),
            Button("1/2 Pot", WIDTH//2 - 80, quick_y, 110, 44, BLUE_BTN, BLUE_BTN_HOVER, 13),
            Button("Pot", WIDTH//2 + 40, quick_y, 90, 44, BLUE_BTN, BLUE_BTN_HOVER, 14),
            Button("All-in", WIDTH//2 + 140, quick_y, 110, 44, ORANGE_BTN, ORANGE_BTN_HOVER, 15),
        ]
        self.buttons = [self.btn_check_call, self.btn_confirm_bet, self.btn_fold, self.btn_next, *self.quick_buttons]
        self.btn_next.active = False

    def sync_input_text(self, value):
        self.input_box.text = value
        self.input_box.txt_surface = font_med.render(value, True, BLACK)

    def get_min_raise_total(self, player):
        if player.chips <= 0:
            return player.round_bet
        return min(player.round_bet + player.chips, max(self.street_high_bet + BIG_BLIND, self.street_high_bet + 1))

    def set_bet_amount(self, target_total):
        if self.turn_index != 0 or self.stage >= 4:
            return

        human = self.players[0]
        capped = int(clamp(target_total, human.round_bet, human.round_bet + human.chips))
        if capped <= human.round_bet:
            self.sync_input_text("")
            return
        self.sync_input_text(str(capped))

    def apply_quick_bet(self, action_code):
        human = self.players[0]
        to_call = max(0, self.street_high_bet - human.round_bet)
        min_raise_total = self.get_min_raise_total(human)

        if action_code == 11:
            self.sync_input_text("")
            return
        if action_code == 12:
            self.set_bet_amount(min_raise_total)
            return
        if action_code == 13:
            target = human.round_bet + to_call + max(BIG_BLIND, int(self.pot * 0.5))
            self.set_bet_amount(max(min_raise_total, target))
            return
        if action_code == 14:
            target = human.round_bet + to_call + max(BIG_BLIND, self.pot)
            self.set_bet_amount(max(min_raise_total, target))
            return
        if action_code == 15:
            self.set_bet_amount(human.round_bet + human.chips)

    def get_blind_indices(self):
        num_p = len(self.players)
        sb_idx = (self.dealer_index + 1) % num_p
        while self.players[sb_idx].chips <= 0:
            sb_idx = (sb_idx + 1) % num_p
        bb_idx = (sb_idx + 1) % num_p
        while self.players[bb_idx].chips <= 0:
            bb_idx = (bb_idx + 1) % num_p
        return sb_idx, bb_idx

    def get_active_order(self, preflop=False):
        num_p = len(self.players)
        if preflop:
            _, bb_idx = self.get_blind_indices()
            start = (bb_idx + 1) % num_p
        else:
            start = (self.dealer_index + 1) % num_p

        order = []
        for i in range(num_p):
            idx = (start + i) % num_p
            p = self.players[idx]
            if p.is_active and not p.has_folded:
                order.append(idx)
        return order

    def get_position_score(self, idx, preflop=False):
        order = self.get_active_order(preflop=preflop)
        if idx not in order or len(order) <= 1:
            return 1.0
        return order.index(idx) / (len(order) - 1)

    def count_live_opponents(self, player):
        return sum(1 for p in self.players if p is not player and p.is_active and not p.has_folded)

    def get_effective_stack(self, player):
        live_stacks = [player.chips + player.round_bet]
        for opp in self.players:
            if opp is player or not opp.is_active or opp.has_folded:
                continue
            live_stacks.append(opp.chips + opp.round_bet)
        return min(live_stacks) if live_stacks else player.chips + player.round_bet

    def board_texture_score(self):
        if len(self.community) < 3:
            return 0.0

        values = sorted(set(c.value for c in self.community))
        value_counts = Counter(c.value for c in self.community)
        suit_counts = Counter(c.suit for c in self.community)

        wetness = 0.0
        max_suit = max(suit_counts.values(), default=0)
        if max_suit >= 3:
            wetness += 0.30
        elif max_suit == 2:
            wetness += 0.08

        if any(count >= 2 for count in value_counts.values()):
            wetness += 0.18

        if values and max(values) - min(values) <= 4:
            wetness += 0.28
        elif values and max(values) - min(values) <= 6:
            wetness += 0.14

        if len(values) >= 4:
            gaps = [values[i + 1] - values[i] for i in range(len(values) - 1)]
            if sum(1 for gap in gaps if gap <= 2) >= 2:
                wetness += 0.12

        return clamp(wetness, 0.0, 1.0)

    def get_draw_info(self, player):
        draw_info = {
            "flush_draw": False,
            "open_ended": False,
            "gutshot": False,
            "combo": False,
            "overcards": 0,
            "score": 0.0,
        }

        if not self.community or len(self.community) >= 5:
            return draw_info

        all_cards = player.hand + self.community
        suit_counts = Counter(c.suit for c in all_cards)
        flush_draw_suit = None
        for suit, count in suit_counts.items():
            if count == 4:
                draw_info["flush_draw"] = True
                flush_draw_suit = suit
                break

        open_ended, gutshot = get_straight_draw_info([c.value for c in all_cards])
        draw_info["open_ended"] = open_ended
        draw_info["gutshot"] = gutshot and not open_ended

        board_high = max((c.value for c in self.community), default=0)
        made_score = evaluate_hand(all_cards)[0]
        if made_score == 0:
            draw_info["overcards"] = sum(1 for c in player.hand if c.value > board_high)

        score = 0.0
        if draw_info["flush_draw"]:
            score += 0.18
        if draw_info["open_ended"]:
            score += 0.16
        elif draw_info["gutshot"]:
            score += 0.08
        if draw_info["overcards"] == 2:
            score += 0.05
        elif draw_info["overcards"] == 1:
            score += 0.02

        if draw_info["flush_draw"] and (draw_info["open_ended"] or draw_info["gutshot"]):
            draw_info["combo"] = True
            score += 0.06

        if draw_info["flush_draw"] and flush_draw_suit is not None:
            if any(c.suit == flush_draw_suit and c.value >= 12 for c in player.hand):
                score += 0.04

        draw_info["score"] = clamp(score, 0.0, 0.40)
        return draw_info

    def estimate_player_equity(self, player):
        opponents = self.count_live_opponents(player)
        if opponents <= 0:
            return 1.0

        stage_sims = {0: 150, 1: 170, 2: 210, 3: 260}
        simulations = stage_sims.get(self.stage, 170) - min(40, (opponents - 1) * 10)
        return estimate_equity(player.hand, self.community, opponents, simulations=max(80, simulations))

    def get_made_hand_strength(self, player):
        score, tie_break, hand_name = evaluate_hand(player.hand + self.community)
        hole_values = [c.value for c in player.hand]
        board_values = sorted([c.value for c in self.community], reverse=True)
        board_top = board_values[0] if board_values else 0
        board_second = board_values[1] if len(board_values) > 1 else board_top

        if score >= 6:
            strength = 0.97
        elif score == 5:
            strength = 0.92
        elif score == 4:
            strength = 0.86
        elif score == 3:
            strength = 0.84
        elif score == 2:
            strength = 0.75
            pair_values = set(tie_break[:2])
            strength += 0.03 * sum(1 for v in hole_values if v in pair_values)
        elif score == 1:
            pair_rank = tie_break[0]
            if pair_rank not in hole_values:
                strength = 0.29
            elif pair_rank >= board_top:
                strength = 0.64
            elif pair_rank >= board_second:
                strength = 0.54
            else:
                strength = 0.44

            kicker_values = [v for v in hole_values if v != pair_rank]
            if kicker_values:
                strength += max(0, kicker_values[0] - 10) * 0.008
        else:
            overcards = sum(1 for v in hole_values if v > board_top)
            strength = 0.12 + 0.03 * overcards

        return score, clamp(strength, 0.05, 0.99), hand_name

    def commit_to_target(self, player, target_total):
        target_total = int(max(player.round_bet, target_total))
        previous_high = self.street_high_bet
        contributed = player.bet(max(0, target_total - player.round_bet))
        self.pot += contributed

        if player.round_bet > self.street_high_bet:
            self.street_high_bet = player.round_bet
            idx = self.players.index(player)
            self.street_last_aggressor = idx
            if self.stage == 0 and player.round_bet > BIG_BLIND:
                self.preflop_last_raiser = idx

        return contributed, player.round_bet > previous_high

    def get_postflop_bet_total(self, fraction):
        return max(BIG_BLIND, int(max(BIG_BLIND * 2, self.pot * fraction)))

    def get_postflop_raise_total(self, to_call, fraction):
        raise_on_top = max(to_call, int((self.pot + to_call) * fraction))
        return max(self.street_high_bet + BIG_BLIND, self.street_high_bet + raise_on_top)

    def decide_bot_action(self, bot):
        idx = self.players.index(bot)
        prof = bot.profile
        rng = random.random()
        to_call = self.street_high_bet - bot.round_bet
        pot_odds = to_call / max(self.pot + to_call, 1) if to_call > 0 else 0.0
        position = self.get_position_score(idx, preflop=(self.stage == 0))
        opponents = self.count_live_opponents(bot)
        effective_stack = self.get_effective_stack(bot)
        spr = effective_stack / max(self.pot, 1)
        equity = self.estimate_player_equity(bot)
        bot.hand_read_strength = equity

        if self.stage == 0:
            hand_score = preflop_hand_strength(bot.hand[0], bot.hand[1])
            unopened = self.preflop_last_raiser is None and self.street_high_bet == BIG_BLIND
            call_threshold = 0.43 - position * 0.07 - prof["loose"] * 0.05 + pot_odds * 0.10
            strong_raise_threshold = 0.72 - prof["aggr"] * 0.05
            open_threshold = 0.47 - position * 0.09 - prof["loose"] * 0.04

            if unopened:
                if hand_score >= strong_raise_threshold or (hand_score >= 0.66 and rng < 0.75 + prof["aggr"] * 0.2):
                    bb_mult = 2.2 + (1.0 - position) * 0.8 + prof["aggr"] * 0.3
                    return "raise", int(BIG_BLIND * bb_mult), "Raise"
                if hand_score >= open_threshold:
                    if to_call == 0 or rng < 0.82:
                        bb_mult = 2.1 + (1.0 - position) * 0.5
                        return "raise", int(BIG_BLIND * bb_mult), "Raise"
                    return "call", None, "Call"
                if to_call == 0:
                    if position > 0.78 and hand_score >= open_threshold - 0.05 and rng < prof["bluff"] * 0.40:
                        return "raise", int(BIG_BLIND * 2.2), "Raise"
                    return "check", None, "Check"
                if to_call <= BIG_BLIND and hand_score >= open_threshold - 0.02 and rng < 0.30 + prof["loose"] * 0.20:
                    return "call", None, "Call"
                return "fold", None, "Fold"

            if hand_score >= 0.82 or (hand_score >= 0.74 and rng < 0.45 + prof["aggr"] * 0.35):
                multiplier = 3.2 if position < 0.45 else 2.8
                return "raise", int(self.street_high_bet * multiplier), "Raise"
            if hand_score >= call_threshold and (to_call / max(bot.chips + bot.round_bet, 1)) < 0.30:
                if hand_score >= 0.70 and rng < 0.18 + prof["aggr"] * 0.20:
                    multiplier = 3.0 if position < 0.45 else 2.7
                    return "raise", int(self.street_high_bet * multiplier), "Raise"
                return "call", None, "Call"
            if to_call == 0:
                return "check", None, "Check"
            return "fold", None, "Fold"

        made_score, made_strength, hand_name = self.get_made_hand_strength(bot)
        draw_info = self.get_draw_info(bot)
        wetness = self.board_texture_score()
        cbet_spot = self.stage == 1 and self.preflop_last_raiser == idx
        continue_threshold = clamp(pot_odds + 0.05 - position * 0.03 - prof["loose"] * 0.02 + wetness * 0.02, 0.12, 0.80)

        if spr < 1.2 and (made_strength >= 0.70 or equity >= max(0.42, pot_odds)):
            if to_call == 0:
                return "raise", bot.round_bet + bot.chips, "All-in"
            return "call", None, "All-in"

        if to_call == 0:
            if made_strength >= 0.90:
                fraction = 0.72 if wetness >= 0.45 else 0.58
                return "bet", self.get_postflop_bet_total(fraction), "Bet"
            if made_strength >= 0.72:
                if rng < 0.74:
                    fraction = 0.58 if wetness >= 0.45 else 0.42
                    return "bet", self.get_postflop_bet_total(fraction), "Bet"
                return "check", None, "Check"
            if draw_info["score"] >= 0.22 and (position > 0.35 or opponents <= 2):
                if rng < 0.46 + prof["bluff"] * 0.28:
                    fraction = 0.62 if draw_info["combo"] else 0.48
                    return "bet", self.get_postflop_bet_total(fraction), "Bet"
            if cbet_spot and (wetness < 0.70 or equity > 0.33):
                if rng < 0.42 + prof["aggr"] * 0.25:
                    fraction = 0.33 if wetness < 0.35 else 0.45
                    return "bet", self.get_postflop_bet_total(fraction), "Bet"
            if position > 0.78 and wetness < 0.30 and rng < prof["bluff"] * 0.22:
                return "bet", self.get_postflop_bet_total(0.35), "Bet"
            return "check", None, "Check"

        bet_pressure = to_call / max(self.pot, 1)
        if made_strength >= 0.94 or equity >= 0.80:
            fraction = 0.95 if wetness >= 0.40 else 0.72
            return "raise", self.get_postflop_raise_total(to_call, fraction), "Raise"
        if made_strength >= 0.76:
            if bet_pressure <= 0.55 and rng < 0.32 + prof["aggr"] * 0.30:
                return "raise", self.get_postflop_raise_total(to_call, 0.58), "Raise"
            return "call", None, "Call"
        if draw_info["score"] >= 0.22 and equity >= continue_threshold - 0.02:
            if draw_info["combo"] and position > 0.45 and bet_pressure < 0.45 and rng < 0.20 + prof["bluff"] * 0.35:
                return "raise", self.get_postflop_raise_total(to_call, 0.55), "Raise"
            return "call", None, "Call"
        if equity >= continue_threshold and (made_strength >= 0.34 or self.stage < 3 or bet_pressure < 0.35):
            return "call", None, "Call"
        if self.stage == 3 and made_strength >= 0.44 and bet_pressure < 0.28 and rng < 0.42 + prof["loose"] * 0.18:
            return "call", None, "Call"
        return "fold", None, "Fold"

    def execute_bot_action(self, bot, action, target_total=None, label=None):
        if action == "fold":
            bot.has_folded = True
            bot.last_action = label or "Fold"
        elif action == "check":
            bot.last_action = label or "Check"
        elif action == "call":
            contributed = bot.bet(max(0, self.street_high_bet - bot.round_bet))
            self.pot += contributed
            if bot.is_all_in:
                bot.last_action = "All-in"
            else:
                bot.last_action = label or "Call"
        elif action in ("bet", "raise"):
            self.commit_to_target(bot, target_total if target_total is not None else self.street_high_bet + BIG_BLIND)
            if bot.is_all_in and bot.round_bet >= self.street_high_bet:
                bot.last_action = "All-in"
            else:
                bot.last_action = label or ("Raise" if action == "raise" else "Bet")
        else:
            bot.last_action = "Check"

        bot.acted_this_street = True
        self.msg = f"{bot.name}: {bot.last_action}"

    def find_safe_start_index(self, start_from):
        num_p = len(self.players)
        for i in range(num_p):
            idx = (start_from + i) % num_p
            p = self.players[idx]
            if p.is_active and not p.has_folded and not p.is_all_in:
                return idx
        return -1

    def start_new_hand(self):
        self.init_game_ui()
        num_p = len(self.players)

        human = self.players[0]
        bots_with_chips = sum(1 for p in self.players[1:] if p.chips > 0)

        if human.chips <= 0:
            self.msg = "Game Over! You lost all chips."
            self.top_status = "GAME OVER"
            return
        if bots_with_chips == 0:
            self.msg = "VICTORY! You beat everyone!"
            self.top_status = "VICTORY"
            return

        self.dealer_index = (self.dealer_index + 1) % num_p
        while self.players[self.dealer_index].chips <= 0:
             self.dealer_index = (self.dealer_index + 1) % num_p

        sb_idx, bb_idx = self.get_blind_indices()

        for p in self.players: p.reset_for_new_hand()

        self.deck = [Card(s, r) for s in SUITS for r in RANKS]
        random.shuffle(self.deck)
        self.community = []
        self.pot = 0
        self.stage = 0
        self.preflop_last_raiser = None
        self.street_last_aggressor = bb_idx

        self.players[sb_idx].bet(SMALL_BLIND)
        self.players[sb_idx].last_action = "SB"
        self.players[bb_idx].bet(BIG_BLIND)
        self.players[bb_idx].last_action = "BB"

        self.pot += (SMALL_BLIND + BIG_BLIND)
        self.street_high_bet = BIG_BLIND

        for _ in range(2):
            for p in self.players:
                if p.is_active:
                    card = self.deck.pop()
                    if not p.is_human: card.is_face_up = False
                    p.hand.append(card)

        self.msg = f"Blinds ${SMALL_BLIND}/${BIG_BLIND}"

        start_search = (bb_idx + 1) % num_p
        self.turn_index = self.find_safe_start_index(start_search)
        self.turn_start_time = time.time()
        self.last_bot_action_time = 0

        self.sync_input_text("")

        if self.turn_index == 0:
            self.update_buttons()

    def check_round_complete(self):
        active_players = [p for p in self.players if not p.has_folded and p.is_active and not p.is_all_in]
        not_folded = [p for p in self.players if not p.has_folded and p.is_active]
        if len(not_folded) <= 1: return True
        if len(active_players) == 0: return True

        for p in active_players:
            if not p.acted_this_street: return False
            if p.round_bet < self.street_high_bet: return False
        return True

    def next_stage(self):
        can_bet_players = [p for p in self.players if not p.has_folded and not p.is_all_in and p.is_active]
        num_p = len(self.players)

        if len(can_bet_players) < 2:
            while self.stage < 3:
                if self.stage == 0: self.community.extend([self.deck.pop() for _ in range(3)])
                else: self.community.append(self.deck.pop())
                self.stage += 1
            self.showdown()
            return

        if self.stage < 3:
            for p in self.players: p.reset_for_next_street()
            self.street_high_bet = 0
            self.street_last_aggressor = None

            if self.stage == 0:
                self.community.extend([self.deck.pop() for _ in range(3)])
                self.msg = "Flop"
            elif self.stage == 1:
                self.community.append(self.deck.pop())
                self.msg = "Turn"
            elif self.stage == 2:
                self.community.append(self.deck.pop())
                self.msg = "River"

            self.stage += 1

            start_search = (self.dealer_index + 1) % num_p
            self.turn_index = self.find_safe_start_index(start_search)
            self.turn_start_time = time.time()

            if self.turn_index == 0:
                self.update_buttons()
        else:
            self.showdown()

    def handle_timeout(self, player):
        to_call = self.street_high_bet - player.round_bet
        if to_call > 0:
            player.has_folded = True
            player.last_action = "Fold (Timeout)"
        else:
            player.last_action = "Check (Timeout)"
        player.acted_this_street = True
        self.msg = f"{player.name} timed out!"
        self.advance_turn()

    def process_turn(self):
        if self.stage == 4:
            self.top_status = "Hand Finished - Click Next Hand"
            return

        if self.turn_index == -1:
            self.advance_turn()
            return

        current_player = self.players[self.turn_index]

        if not current_player.is_active or current_player.has_folded or current_player.is_all_in:
            self.advance_turn()
            return

        current_sys_time = time.time()
        time_elapsed = current_sys_time - self.turn_start_time
        if time_elapsed > TURN_TIME_LIMIT:
            self.handle_timeout(current_player)
            return

        # --- HUMAN TURN ---
        if current_player.is_human:
            self.top_status = f"YOUR TURN! ({int(TURN_TIME_LIMIT - time_elapsed)}s)"
            self.update_buttons()
            return

        # --- BOT TURN ---
        self.top_status = f"Waiting for {current_player.name}..."
        for btn in self.buttons: btn.active = False
        self.input_box.active = False

        if self.last_bot_action_time == 0:
             self.last_bot_action_time = pygame.time.get_ticks()

        if pygame.time.get_ticks() - self.last_bot_action_time < BOT_ACTION_DELAY_MS: return

        bot = current_player
        action, target_total, label = self.decide_bot_action(bot)
        self.execute_bot_action(bot, action, target_total, label)
        self.advance_turn()

    def advance_turn(self):
        if self.check_round_complete():
            self.next_stage()
            return

        self.turn_index = self.find_safe_start_index(self.turn_index + 1)
        self.turn_start_time = time.time()
        self.last_bot_action_time = 0

    def human_act(self, action_code):
        if self.turn_index != 0: return

        human = self.players[0]
        to_call = self.street_high_bet - human.round_bet

        if action_code >= 11:
            self.apply_quick_bet(action_code)
            return

        if action_code == 1:
            if to_call > 0:
                amt = human.bet(to_call)
                self.pot += amt
                human.last_action = "Call" if not human.is_all_in else "All-in"
            else:
                human.last_action = "Check"

        elif action_code == 2:
            try:
                bet_amount = int(self.input_box.text)
            except ValueError:
                self.msg = "Invalid Number"
                return

            min_valid = self.street_high_bet
            if bet_amount <= min_valid:
                self.msg = f"Must bet > {min_valid}"
                return

            needed = bet_amount - human.round_bet
            if needed > human.chips:
                needed = human.chips
                bet_amount = human.round_bet + needed

            amt = human.bet(needed)
            self.pot += amt

            if human.round_bet > self.street_high_bet:
                self.street_high_bet = human.round_bet
                self.street_last_aggressor = 0
                if self.stage == 0 and human.round_bet > BIG_BLIND:
                    self.preflop_last_raiser = 0

            human.last_action = "Raise" if not human.is_all_in else "All-in"
            self.sync_input_text("")

        elif action_code == 3:
            human.has_folded = True
            human.last_action = "Fold"

        human.acted_this_street = True
        self.advance_turn()

    def update_buttons(self):
        human = self.players[0]
        to_call = self.street_high_bet - human.round_bet

        self.input_box.active = True
        for btn in self.buttons:
            btn.active = True
            if btn.action_code == 4: btn.active = False

        if to_call > 0:
            if human.chips <= to_call:
                self.btn_check_call.text = "All-in!"
                self.btn_check_call.base_color = RED_BTN
                self.btn_confirm_bet.active = False
                self.input_box.active = False
            else:
                self.btn_check_call.text = f"Call ${to_call}"
                self.btn_check_call.base_color = BLUE_BTN
        else:
            self.btn_check_call.text = "Check"
            self.btn_check_call.base_color = WSOP_BLUE

        self.btn_confirm_bet.text = "Bet/Raise"
        for quick_btn in self.quick_buttons:
            quick_btn.active = human.chips > 0 and self.btn_confirm_bet.active

    def handle_event(self, event):
        if self.turn_index == 0 and self.stage < 4:
            self.input_box.handle_event(event)

    def showdown(self):
        active_hands = []
        for p in self.players:
            if not p.has_folded and p.is_active:
                for c in p.hand: c.is_face_up = True
                score, tie_break, name = evaluate_hand(p.hand + self.community)
                active_hands.append((score, tie_break, p, name))

        if not active_hands:
            self.msg = "All folded"
        elif len(active_hands) == 1:
            winner = active_hands[0][2]
            winner.chips += self.pot
            winner.win_desc = f"+${self.pot} (Opponent Folded)"
            self.msg = f"{winner.name} Wins!"
        else:
            # Sort DESC by score, then tie_break list
            active_hands.sort(key=lambda x: (x[0], x[1]), reverse=True)

            winner_score = active_hands[0][0]
            winner_tie_list = active_hands[0][1]

            winners = []
            for entry in active_hands:
                if entry[0] == winner_score and entry[1] == winner_tie_list:
                    winners.append(entry[2])
                else:
                    break

            prize = self.pot // len(winners)
            for w in winners:
                w.chips += prize
                w_hand_name = next(x[3] for x in active_hands if x[2] == w)
                w.win_desc = f"+${prize} ({w_hand_name})"

            names = " & ".join([w.name for w in winners])
            self.msg = f"Winner: {names} +${prize}"

        self.stage = 4
        self.top_status = "Round Over"
        self.buttons = [self.btn_next]
        self.btn_next.active = True
        self.input_box.active = False

    def draw_win_label(self, player):
        if player.win_desc:
            bx, by = player.bet_x, player.bet_y
            txt = font_win.render(player.win_desc, True, WSOP_ACCENT)
            txt_rect = txt.get_rect(center=(bx, by - 30))
            bg_rect = txt_rect.inflate(20, 10)
            pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect, border_radius=10)
            pygame.draw.rect(screen, WSOP_ACCENT, bg_rect, 2, border_radius=10)
            screen.blit(txt, txt_rect)

    def draw_markers(self, player, idx):
        marker_y = player.y - 45
        marker_x = player.x - 20
        markers = []
        if idx == self.dealer_index: markers.append(("D", ORANGE_MARKER))

        sb_calc, bb_calc = self.get_blind_indices()
        if idx == sb_calc: markers.append(("SB", PURPLE_SB))
        if idx == bb_calc: markers.append(("BB", BLUE_BB))

        for text, color in markers:
            pygame.draw.circle(screen, color, (marker_x, marker_y), 15)
            pygame.draw.circle(screen, WHITE, (marker_x, marker_y), 15, 1)
            t_surf = font_small.render(text, True, WHITE)
            t_rect = t_surf.get_rect(center=(marker_x, marker_y))
            screen.blit(t_surf, t_rect)
            marker_x -= 35

    def draw_table_bet_and_status(self, player):
        bx, by = player.bet_x, player.bet_y
        if player.round_bet > 0:
            bet_txt = font_bet_amount.render(f"${player.round_bet}", True, WSOP_ACCENT)
            screen.blit(bet_txt, (bx + 15, by - 10))

        if player.last_action:
            bg_color = GRAY
            if "Fold" in player.last_action: bg_color = RED_BTN
            elif "Bet" in player.last_action or "Raise" in player.last_action or "All-in" in player.last_action: bg_color = ORANGE_BTN
            elif "Check" in player.last_action: bg_color = WSOP_BLUE
            elif "Call" in player.last_action: bg_color = BLUE_BTN

            act_surf = font_small.render(player.last_action, True, WHITE)
            act_rect = act_surf.get_rect(center=(bx, by - 30))
            bg_rect = act_rect.inflate(10, 10)
            pygame.draw.rect(screen, bg_color, bg_rect, border_radius=5)
            screen.blit(act_surf, act_rect)

    def draw_table_background(self):
        screen.fill((5, 10, 20))

        rail_rect = pygame.Rect(50, 80, WIDTH-100, HEIGHT-260)
        pygame.draw.ellipse(screen, WSOP_BORDER, rail_rect)
        felt_rect = rail_rect.inflate(-40, -40)
        pygame.draw.ellipse(screen, WSOP_BLUE, felt_rect)
        line_rect = felt_rect.inflate(-20, -20)
        pygame.draw.ellipse(screen, FELT_LINE, line_rect, 2)

        logo_surf = font_huge.render("WORLD SERIES", True, WSOP_ACCENT)
        logo_rect = logo_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 40))
        screen.blit(logo_surf, logo_rect)
        logo_sub = font_huge.render("OF POKER", True, WSOP_ACCENT)
        logo_sub_rect = logo_sub.get_rect(center=(WIDTH//2, HEIGHT//2 + 30))
        screen.blit(logo_sub, logo_sub_rect)

    def draw(self):
        self.draw_table_background()

        comm_scale = 1.3
        comm_w = int(CARD_WIDTH * comm_scale)
        comm_start = WIDTH//2 - (2.5 * comm_w) - 10
        comm_y = HEIGHT//2 - 120 + 40 
        for i, c in enumerate(self.community):
            c.draw(screen, comm_start + i * (comm_w + 5), comm_y, scale=comm_scale)

        for i, p in enumerate(self.players):
            name_rect = pygame.Rect(p.x, p.y - 40, 130, 35)
            is_turn = (i == self.turn_index and self.stage < 4)
            border_col = WSOP_ACCENT if is_turn else BLACK
            border_width = 3 if is_turn else 2

            pygame.draw.rect(screen, (20, 20, 20), name_rect, border_radius=5)
            pygame.draw.rect(screen, border_col, name_rect, border_width, border_radius=5)

            name_col = WHITE if p.is_active else RED
            txt = font_med.render(f"{p.name}: ${p.chips}", True, name_col)
            screen.blit(txt, (p.x + 5, p.y - 35))

            if p.profile:
                style_txt = font_tiny.render(f"({p.profile['style']})", True, (150, 150, 150))
                screen.blit(style_txt, (p.x + 5, p.y - 15))

            if is_turn and not p.has_folded and self.stage < 4:
                time_elapsed = time.time() - self.turn_start_time
                time_left = max(0, TURN_TIME_LIMIT - time_elapsed)
                timer_str = f"{int(time_left)}s"
                timer_surf = font_timer.render(timer_str, True, TIMER_RED)
                screen.blit(timer_surf, (p.x + 135, p.y - 35))

            if p.has_folded:
                fold_txt = font_med.render("FOLD", True, RED)
                screen.blit(fold_txt, (p.x + 30, p.y + 40))
            elif p.is_active:
                for idx, card in enumerate(p.hand):
                    card.draw(screen, p.x + idx * (CARD_WIDTH + 5), p.y)

            self.draw_markers(p, i)
            self.draw_table_bet_and_status(p)
            self.draw_win_label(p)

        pot_txt = font_large.render(f"POT: ${self.pot}", True, WSOP_ACCENT)
        pot_rect = pot_txt.get_rect(topright=(WIDTH - 40, 30))
        pygame.draw.rect(screen, (0, 0, 0, 150), pot_rect.inflate(20, 10), border_radius=10)
        pygame.draw.rect(screen, WSOP_BORDER, pot_rect.inflate(20, 10), 2, border_radius=10)
        screen.blit(pot_txt, pot_rect)

        status_bg = pygame.Rect(20, 20, 350, 50)
        pygame.draw.rect(screen, (10, 10, 30), status_bg, border_radius=10)
        pygame.draw.rect(screen, WSOP_BORDER, status_bg, 2, border_radius=10)

        status_txt = font_med.render(self.top_status, True, WSOP_ACCENT)
        screen.blit(status_txt, (40, 32))

        for btn in self.buttons:
            if btn.action_code != 4 or self.stage == 4:
                btn.draw(screen)

        if self.turn_index == 0 and self.stage < 4 and not self.players[0].has_folded:
             self.input_box.update()
             self.input_box.draw(screen)

        return

def handle_pointer_down(game, pos):
    if game.input_box and game.turn_index == 0:
        game.input_box.active = game.input_box.rect.collidepoint(pos)

    for btn in game.buttons:
        if btn.is_clicked(pos):
            if btn.action_code == 4:
                game.start_new_hand()
            else:
                game.human_act(btn.action_code)
            break


def run_frame(game):
    running = True
    game.process_turn()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            refresh_window(event.size)

        game.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN:
            handle_pointer_down(game, to_virtual_pos(event.pos))
        elif event.type == pygame.FINGERDOWN:
            touch_pos = (int(event.x * window.get_width()), int(event.y * window.get_height()))
            handle_pointer_down(game, to_virtual_pos(touch_pos))

    game.draw()
    present_frame()
    return running


def run_game():
    refresh_window()
    game = PokerGame()
    clock = pygame.time.Clock()
    running = True

    while running:
        running = run_frame(game)
        clock.tick(30)

    pygame.quit()


async def run_game_web():
    refresh_window()
    game = PokerGame()
    clock = pygame.time.Clock()
    running = True

    while running:
        running = run_frame(game)
        clock.tick(30)
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    if sys.platform == "emscripten":
        asyncio.run(run_game_web())
    else:
        run_game()
