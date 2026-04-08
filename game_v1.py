import pygame
import random
import time
import json
from collections import Counter, defaultdict
from datetime import datetime
import itertools

# --- 1. Configuration & Initialization ---
pygame.init()

WIDTH, HEIGHT = 1400, 900
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Texas Hold'em Pro Trainer - 8 Player Ring Game")

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
GREEN = (50, 205, 50)
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
GREEN_BTN = (34, 139, 34)
GREEN_BTN_HOVER = (50, 205, 50)

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
font_hud = pygame.font.SysFont("arial", 12, bold=True)

# Suit Font
font_suit = pygame.font.SysFont("segoeuisymbol", 40)
if font_suit.get_height() < 20:
    font_suit = pygame.font.SysFont("arial", 40)

# Game Parameters
CARD_WIDTH, CARD_HEIGHT = 60, 90
INITIAL_STACK = 100000
SMALL_BLIND = 10
BIG_BLIND = 20
TURN_TIME_LIMIT = 30

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUES = {r: i for i, r in enumerate(RANKS, 2)}

# Training Mode
TRAINING_MODE = True  # Set to True to enable training features
SHOW_ADVICE = True
SHOW_EQUITY = True
SHOW_POT_ODDS = True

# --- Bot Profiles ---
BOT_PROFILES = [
    {"name": "Eltonzeng", "style": "LAG", "aggr": 0.85, "loose": 0.80, "bluff": 0.70, "vpip": 0, "pfr": 0, "three_bet": 0},
    {"name": "andy", "style": "TAG", "aggr": 0.60, "loose": 0.25, "bluff": 0.15, "vpip": 0, "pfr": 0, "three_bet": 0},
    {"name": "Tan Xuan", "style": "Maniac", "aggr": 0.95, "loose": 0.90, "bluff": 0.80, "vpip": 0, "pfr": 0, "three_bet": 0},
    {"name": "Rui Cao", "style": "Balanced", "aggr": 0.65, "loose": 0.50, "bluff": 0.40, "vpip": 0, "pfr": 0, "three_bet": 0},
    {"name": "Tom Dwan", "style": "Tricky", "aggr": 0.80, "loose": 0.70, "bluff": 0.70, "vpip": 0, "pfr": 0, "three_bet": 0},
    {"name": "Phil Ivey", "style": "GTO", "aggr": 0.70, "loose": 0.40, "bluff": 0.50, "vpip": 0, "pfr": 0, "three_bet": 0},
    {"name": "Jungleman", "style": "Math", "aggr": 0.50, "loose": 0.30, "bluff": 0.20, "vpip": 0, "pfr": 0, "three_bet": 0},
]

# --- Hand Rankings for Starting Hands ---
PREMIUM_HANDS = [
    ('A', 'A'), ('K', 'K'), ('Q', 'Q'), ('J', 'J'), 
    ('A', 'K', 's')
]

STRONG_HANDS = [
    ('10', '10'), ('A', 'Q', 's'), ('A', 'K'), ('A', 'J', 's'),
    ('K', 'Q', 's'), ('9', '9'), ('8', '8')
]

PLAYABLE_HANDS = [
    ('A', 'Q'), ('A', '10', 's'), ('K', 'J', 's'), ('Q', 'J', 's'),
    ('J', '10', 's'), ('7', '7'), ('6', '6'), ('A', 'J'),
    ('K', 'Q'), ('A', '10')
]

# Position advantages
POSITION_FACTOR = {
    0: 1.0,  # UTG - tightest
    1: 1.05,
    2: 1.1,
    3: 1.15,
    4: 1.2,
    5: 1.25,  # Cutoff
    6: 1.3,   # Button - loosest
    7: 1.1    # SB
}

# --- 2. Hand Evaluation Logic ---
def evaluate_hand(cards):
    """Evaluate poker hand strength"""
    if not cards: 
        return (0, [], "")
    
    values = sorted([c.value for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    suit_counts = Counter(suits)
    value_counts = Counter(values)

    is_flush, flush_suit = False, None
    for s, c in suit_counts.items():
        if c >= 5: 
            is_flush, flush_suit = True, s

    flush_cards = sorted([c.value for c in cards if c.suit == flush_suit], reverse=True) if is_flush else []

    def get_straight(vals):
        uniq = sorted(list(set(vals)), reverse=True)
        if {14, 5, 4, 3, 2}.issubset(set(uniq)): 
            return 5
        for i in range(len(uniq) - 4):
            if uniq[i] - uniq[i+4] == 4: 
                return uniq[i]
        return None

    straight_high = get_straight(values)

    if is_flush:
        sf_high = get_straight(flush_cards)
        if sf_high: 
            return (8, [sf_high], "Straight Flush")

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

    if is_flush: 
        return (5, flush_cards[:5], "Flush")
    if straight_high: 
        return (4, [straight_high], "Straight")

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

def calculate_equity(hero_hand, community, num_opponents=1, iterations=1000):
    """Monte Carlo simulation to calculate equity"""
    if not hero_hand or len(hero_hand) != 2:
        return 0.0
    
    wins = 0
    ties = 0
    
    # Create deck without hero's cards and community cards
    used_cards = set([(c.suit, c.rank) for c in hero_hand + community])
    deck = []
    for suit in SUITS:
        for rank in RANKS:
            if (suit, rank) not in used_cards:
                deck.append(Card(suit, rank))
    
    for _ in range(iterations):
        random.shuffle(deck)
        
        # Deal remaining community cards
        remaining_comm = 5 - len(community)
        full_community = community + deck[:remaining_comm]
        
        # Deal opponent hands
        opp_start = remaining_comm
        hero_score = evaluate_hand(hero_hand + full_community)
        
        best_opp_score = None
        for opp in range(num_opponents):
            opp_hand = deck[opp_start + opp*2:opp_start + opp*2 + 2]
            opp_score = evaluate_hand(opp_hand + full_community)
            if best_opp_score is None or (opp_score[0], opp_score[1]) > (best_opp_score[0], best_opp_score[1]):
                best_opp_score = opp_score
        
        if (hero_score[0], hero_score[1]) > (best_opp_score[0], best_opp_score[1]):
            wins += 1
        elif (hero_score[0], hero_score[1]) == (best_opp_score[0], best_opp_score[1]):
            ties += 1
    
    return (wins + ties * 0.5) / iterations

def count_outs(hand, community):
    """Count outs (cards that improve the hand)"""
    if len(community) < 3:
        return 0, []
    
    current_score = evaluate_hand(hand + community)
    outs = []
    
    used_cards = set([(c.suit, c.rank) for c in hand + community])
    
    for suit in SUITS:
        for rank in RANKS:
            if (suit, rank) not in used_cards:
                test_card = Card(suit, rank)
                test_community = community + [test_card]
                new_score = evaluate_hand(hand + test_community)
                
                if (new_score[0], new_score[1]) > (current_score[0], current_score[1]):
                    outs.append(f"{rank}{suit}")
    
    return len(outs), outs

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
            if self.action_code == 4: 
                return
            draw_col = DISABLED_GRAY
        else:
            mouse_pos = pygame.mouse.get_pos()
            is_hover = self.rect.collidepoint(mouse_pos)
            draw_col = self.hover_color if is_hover else self.base_color

        shadow_rect = self.rect.move(2, 2)
        pygame.draw.rect(surface, (30, 30, 30), shadow_rect, border_radius=8)
        pygame.draw.rect(surface, draw_col, self.rect, border_radius=8)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2, border_radius=8)

        txt_col = WHITE if self.active else (50, 50, 50)
        txt_surf = font_small.render(self.text, True, txt_col)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)

    def is_clicked(self, pos):
        return self.active and self.rect.collidepoint(pos)

class InputBox:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = ''
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                return self.text
            elif event.unicode.isdigit():
                self.text += event.unicode
        return None

    def update(self):
        pass

    def draw(self, surface):
        bg_col = INPUT_ACTIVE if self.active else INPUT_BG
        pygame.draw.rect(surface, bg_col, self.rect, border_radius=5)
        pygame.draw.rect(surface, WSOP_ACCENT if self.active else BLACK, self.rect, 2, border_radius=5)
        
        txt_surf = font_small.render(self.text if self.text else "Amount...", True, BLACK if self.text else GRAY)
        surface.blit(txt_surf, (self.rect.x + 5, self.rect.y + 8))

# --- 4. Player Class ---
class Player:
    def __init__(self, name, x, y, is_human=False, profile=None):
        self.name = name
        self.chips = INITIAL_STACK
        self.hand = []
        self.x, self.y = x, y
        self.is_human = is_human
        self.is_active = True
        self.has_folded = False
        self.round_bet = 0
        self.last_action = ""
        self.win_desc = ""
        self.bet_x = x + 65
        self.bet_y = y + 120
        self.profile = profile
        
        # Statistics
        self.hands_played = 0
        self.vpip_count = 0  # Voluntarily Put In Pot
        self.pfr_count = 0   # Pre-Flop Raise
        self.three_bet_count = 0
        self.total_hands = 0
        self.showdowns_won = 0
        self.showdowns_seen = 0
        
        # Hand history
        self.position_history = []

    def get_vpip(self):
        if self.total_hands == 0:
            return 0
        return int((self.vpip_count / self.total_hands) * 100)
    
    def get_pfr(self):
        if self.total_hands == 0:
            return 0
        return int((self.pfr_count / self.total_hands) * 100)
    
    def get_3bet(self):
        if self.total_hands == 0:
            return 0
        return int((self.three_bet_count / self.total_hands) * 100)

    def reset_for_hand(self):
        self.hand = []
        self.has_folded = False
        self.round_bet = 0
        self.last_action = ""
        self.win_desc = ""
        self.is_active = True

# --- 5. Poker Game Class ---
class PokerGame:
    def __init__(self):
        self.deck = []
        self.community = []
        self.pot = 0
        self.current_bet = 0
        self.stage = 0
        self.msg = ""
        self.top_status = "New Game"
        
        # Hand history
        self.hand_history = []
        self.current_hand_log = []
        self.hand_number = 0
        
        # Training mode
        self.show_training_panel = TRAINING_MODE
        self.advice_text = ""
        self.equity_text = ""
        self.pot_odds_text = ""
        
        # Player positions (8-max table layout)
        positions = [
            (550, 650),   # Position 0: Human (bottom)
            (250, 600),   # Position 1: Left-bottom
            (100, 400),   # Position 2: Left-middle
            (150, 180),   # Position 3: Left-top
            (450, 100),   # Position 4: Top-left
            (750, 100),   # Position 5: Top-right
            (1050, 180),  # Position 6: Right-top
            (1100, 400),  # Position 7: Right-middle
        ]
        
        self.players = [Player("You", *positions[0], is_human=True, profile=None)]
        for i, profile in enumerate(BOT_PROFILES):
            self.players.append(Player(
                profile["name"],
                *positions[i+1],
                is_human=False,
                profile=profile
            ))
        
        self.dealer_index = 0
        self.turn_index = 0
        self.turn_start_time = 0
        
        # UI Elements
        btn_y = HEIGHT - 100
        btn_spacing = 140
        btn_start_x = 50
        
        self.btn_fold = Button("Fold", btn_start_x, btn_y, 120, 50, RED_BTN, RED_BTN_HOVER, 0)
        self.btn_check = Button("Check/Call", btn_start_x + btn_spacing, btn_y, 120, 50, BLUE_BTN, BLUE_BTN_HOVER, 1)
        self.btn_bet = Button("Bet/Raise", btn_start_x + btn_spacing*2, btn_y, 120, 50, ORANGE_BTN, ORANGE_BTN_HOVER, 2)
        self.btn_all_in = Button("All-In", btn_start_x + btn_spacing*3, btn_y, 120, 50, GOLD_BTN, ORANGE_BTN_HOVER, 3)
        self.btn_next = Button("Next Hand", btn_start_x + btn_spacing*4, btn_y, 120, 50, GREEN_BTN, GREEN_BTN_HOVER, 4)
        
        self.buttons = [self.btn_fold, self.btn_check, self.btn_bet, self.btn_all_in]
        self.input_box = InputBox(btn_start_x + btn_spacing*2, btn_y + 60, 120, 30)
        
        self.start_new_hand()

    def log_action(self, player, action, amount=0):
        """Log action to current hand history"""
        log_entry = {
            "player": player.name,
            "action": action,
            "amount": amount,
            "stage": ["Pre-Flop", "Flop", "Turn", "River"][min(self.stage, 3)],
            "pot": self.pot,
            "position": self.players.index(player)
        }
        self.current_hand_log.append(log_entry)

    def save_hand_history(self):
        """Save completed hand to history"""
        hand_record = {
            "hand_number": self.hand_number,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "actions": self.current_hand_log.copy(),
            "final_pot": self.pot,
            "community": [(c.suit, c.rank) for c in self.community],
            "winner": self.msg
        }
        self.hand_history.append(hand_record)
        self.current_hand_log = []

    def get_position_name(self, idx):
        """Get position name relative to dealer"""
        num_p = len(self.players)
        pos_from_dealer = (idx - self.dealer_index) % num_p
        
        if pos_from_dealer == 0:
            return "BTN"
        elif pos_from_dealer == 1:
            return "SB"
        elif pos_from_dealer == 2:
            return "BB"
        elif pos_from_dealer == 3:
            return "UTG"
        elif pos_from_dealer == num_p - 1:
            return "CO"
        else:
            return f"MP{pos_from_dealer - 2}"

    def calculate_pot_odds(self):
        """Calculate pot odds for current decision"""
        if self.current_bet == 0:
            return 0, "No bet to call"
        
        to_call = self.current_bet - self.players[0].round_bet
        if to_call <= 0:
            return 0, "Already called"
        
        pot_odds = to_call / (self.pot + to_call)
        return pot_odds, f"Pot Odds: {pot_odds*100:.1f}% (need {pot_odds*100:.1f}% equity to call)"

    def get_preflop_advice(self, hand, position_idx):
        """Give advice for pre-flop play based on hand and position"""
        if not hand or len(hand) != 2:
            return "Waiting for cards..."
        
        card1, card2 = hand[0], hand[1]
        rank1, rank2 = card1.rank, card2.rank
        suited = card1.suit == card2.suit
        
        # Normalize hand representation
        if RANK_VALUES[rank1] < RANK_VALUES[rank2]:
            rank1, rank2 = rank2, rank1
        
        hand_str = (rank1, rank2, 's') if suited else (rank1, rank2)
        
        position_name = self.get_position_name(position_idx)
        
        # Check hand strength
        if hand_str in PREMIUM_HANDS or (rank1, rank2) in PREMIUM_HANDS:
            return f"PREMIUM HAND! Raise from {position_name}. 3-bet if facing raise."
        elif hand_str in STRONG_HANDS or (rank1, rank2) in STRONG_HANDS:
            if position_idx >= 3:
                return f"STRONG HAND. Raise from {position_name}."
            else:
                return f"STRONG HAND. Raise or call from {position_name}."
        elif hand_str in PLAYABLE_HANDS or (rank1, rank2) in PLAYABLE_HANDS:
            if position_idx >= 5:
                return f"PLAYABLE from {position_name}. Raise if unopened."
            else:
                return f"MARGINAL from {position_name}. Fold to raise, call if cheap."
        else:
            # Check for high cards
            if RANK_VALUES[rank1] >= 11:  # J or higher
                if position_idx >= 5:
                    return f"SPECULATIVE from {position_name}. Can call if pot is small."
                else:
                    return f"WEAK from {position_name}. Fold unless in blinds with good odds."
            else:
                return f"FOLD from {position_name}. Too weak to play profitably."

    def start_new_hand(self):
        """Start a new hand"""
        self.hand_number += 1
        self.current_hand_log = []
        
        # Reset players
        for p in self.players:
            p.reset_for_hand()
            p.total_hands += 1
        
        # Move dealer button
        self.dealer_index = (self.dealer_index + 1) % len(self.players)
        
        # Create and shuffle deck
        self.deck = [Card(s, r) for s in SUITS for r in RANKS]
        random.shuffle(self.deck)
        
        self.community = []
        self.pot = 0
        self.current_bet = 0
        self.stage = 0
        self.msg = ""
        
        # Deal cards
        for _ in range(2):
            for p in self.players:
                if p.chips > 0:
                    p.hand.append(self.deck.pop())
        
        # Hide bot cards
        for p in self.players[1:]:
            for c in p.hand:
                c.is_face_up = False
        
        # Post blinds
        self.post_blinds()
        
        # Set first player after BB
        num_p = len(self.players)
        sb_idx = (self.dealer_index + 1) % num_p
        while self.players[sb_idx].chips <= 0:
            sb_idx = (sb_idx + 1) % num_p
        
        bb_idx = (sb_idx + 1) % num_p
        while self.players[bb_idx].chips <= 0:
            bb_idx = (bb_idx + 1) % num_p
        
        self.turn_index = (bb_idx + 1) % num_p
        while self.players[self.turn_index].chips <= 0 or self.players[self.turn_index].has_folded:
            self.turn_index = (self.turn_index + 1) % num_p
        
        self.turn_start_time = time.time()
        self.top_status = "Pre-Flop"
        self.buttons = [self.btn_fold, self.btn_check, self.btn_bet, self.btn_all_in]
        self.input_box.active = False
        self.input_box.text = ''
        
        # Update advice for human player
        if SHOW_ADVICE and not self.players[0].has_folded:
            self.advice_text = self.get_preflop_advice(self.players[0].hand, 0)

    def post_blinds(self):
        """Post small and big blinds"""
        num_p = len(self.players)
        
        # Find SB
        sb_idx = (self.dealer_index + 1) % num_p
        while self.players[sb_idx].chips <= 0:
            sb_idx = (sb_idx + 1) % num_p
        
        sb_player = self.players[sb_idx]
        sb_amount = min(SMALL_BLIND, sb_player.chips)
        sb_player.chips -= sb_amount
        sb_player.round_bet = sb_amount
        self.pot += sb_amount
        sb_player.last_action = f"SB ${sb_amount}"
        self.log_action(sb_player, "Small Blind", sb_amount)
        
        # Find BB
        bb_idx = (sb_idx + 1) % num_p
        while self.players[bb_idx].chips <= 0:
            bb_idx = (bb_idx + 1) % num_p
        
        bb_player = self.players[bb_idx]
        bb_amount = min(BIG_BLIND, bb_player.chips)
        bb_player.chips -= bb_amount
        bb_player.round_bet = bb_amount
        self.pot += bb_amount
        self.current_bet = bb_amount
        bb_player.last_action = f"BB ${bb_amount}"
        self.log_action(bb_player, "Big Blind", bb_amount)

    def handle_event(self, event):
        """Handle pygame events"""
        result = self.input_box.handle_event(event)
        if result:
            self.input_box.active = False

    def human_act(self, action_code):
        """Handle human player action"""
        if self.turn_index != 0 or self.stage >= 4:
            return
        
        player = self.players[0]
        
        if action_code == 0:  # Fold
            player.has_folded = True
            player.last_action = "Fold"
            self.log_action(player, "Fold")
            
        elif action_code == 1:  # Check/Call
            to_call = self.current_bet - player.round_bet
            if to_call == 0:
                player.last_action = "Check"
                self.log_action(player, "Check")
            else:
                call_amt = min(to_call, player.chips)
                player.chips -= call_amt
                player.round_bet += call_amt
                self.pot += call_amt
                player.last_action = f"Call ${call_amt}"
                self.log_action(player, "Call", call_amt)
                
                # Update VPIP
                if self.stage == 0 and to_call > 0:
                    player.vpip_count += 1
                    
        elif action_code == 2:  # Bet/Raise
            try:
                amount = int(self.input_box.text) if self.input_box.text else 0
                to_call = self.current_bet - player.round_bet
                
                if amount < to_call * 2:
                    amount = to_call * 2
                
                amount = min(amount, player.chips)
                if amount > 0:
                    player.chips -= amount
                    player.round_bet += amount
                    self.pot += amount
                    if self.current_bet > 0:
                        player.last_action = f"Raise ${amount}"
                        self.log_action(player, "Raise", amount)
                        
                        # Update PFR and 3-bet
                        if self.stage == 0:
                            player.pfr_count += 1
                            if self.current_bet > BIG_BLIND:
                                player.three_bet_count += 1
                    else:
                        player.last_action = f"Bet ${amount}"
                        self.log_action(player, "Bet", amount)
                        if self.stage == 0:
                            player.pfr_count += 1
                    
                    self.current_bet = player.round_bet
                    self.input_box.text = ''
                    
                    # Update VPIP
                    if self.stage == 0:
                        player.vpip_count += 1
            except:
                pass
                
        elif action_code == 3:  # All-in
            all_in_amt = player.chips
            player.chips = 0
            player.round_bet += all_in_amt
            self.pot += all_in_amt
            player.last_action = f"All-in ${all_in_amt}"
            self.log_action(player, "All-in", all_in_amt)
            if all_in_amt > self.current_bet:
                self.current_bet = player.round_bet
            
            # Update VPIP and potentially PFR
            if self.stage == 0:
                player.vpip_count += 1
                if all_in_amt > self.current_bet:
                    player.pfr_count += 1
        
        self.advance_turn()

    def bot_act(self, player_idx):
        """AI decision making for bot players"""
        player = self.players[player_idx]
        profile = player.profile
        
        if not profile:
            return
        
        to_call = self.current_bet - player.round_bet
        pot_size = self.pot
        
        # Position factor
        position = self.get_position_name(player_idx)
        pos_idx = player_idx
        pos_factor = POSITION_FACTOR.get(pos_idx, 1.0)
        
        # Adjust aggression and looseness by position
        adj_aggr = profile['aggr'] * pos_factor
        adj_loose = profile['loose'] * pos_factor
        
        # Stage-specific adjustments
        if self.stage == 0:  # Pre-flop
            # Check hand strength (simplified)
            if player.hand:
                card1, card2 = player.hand[0], player.hand[1]
                hand_strength = (card1.value + card2.value) / 28  # Normalize to 0-1
                is_pair = card1.value == card2.value
                is_suited = card1.suit == card2.suit
                
                if is_pair:
                    hand_strength += 0.2
                if is_suited:
                    hand_strength += 0.1
                
                hand_strength = min(1.0, hand_strength)
            else:
                hand_strength = 0.5
            
            # Decision logic
            if to_call == 0:  # No bet to call
                if random.random() < adj_aggr * hand_strength:
                    # Bet
                    bet_amt = int(pot_size * random.uniform(0.5, 1.0))
                    bet_amt = min(bet_amt, player.chips)
                    if bet_amt >= BIG_BLIND:
                        player.chips -= bet_amt
                        player.round_bet += bet_amt
                        self.pot += bet_amt
                        self.current_bet = player.round_bet
                        player.last_action = f"Bet ${bet_amt}"
                        self.log_action(player, "Bet", bet_amt)
                        
                        # Update stats
                        if self.stage == 0:
                            player.vpip_count += 1
                            player.pfr_count += 1
                    else:
                        player.last_action = "Check"
                        self.log_action(player, "Check")
                else:
                    player.last_action = "Check"
                    self.log_action(player, "Check")
            else:
                # Facing a bet
                pot_odds = to_call / (pot_size + to_call)
                
                # Should we call?
                call_threshold = pot_odds * (2 - adj_loose)
                
                if hand_strength >= call_threshold:
                    # Should we raise?
                    if random.random() < adj_aggr * hand_strength and player.chips > to_call * 2:
                        raise_amt = min(int(to_call * random.uniform(2, 3.5)), player.chips)
                        player.chips -= raise_amt
                        player.round_bet += raise_amt
                        self.pot += raise_amt
                        self.current_bet = player.round_bet
                        player.last_action = f"Raise ${raise_amt}"
                        self.log_action(player, "Raise", raise_amt)
                        
                        # Update stats
                        if self.stage == 0:
                            player.vpip_count += 1
                            player.pfr_count += 1
                            if self.current_bet > BIG_BLIND:
                                player.three_bet_count += 1
                    else:
                        # Call
                        call_amt = min(to_call, player.chips)
                        player.chips -= call_amt
                        player.round_bet += call_amt
                        self.pot += call_amt
                        player.last_action = f"Call ${call_amt}"
                        self.log_action(player, "Call", call_amt)
                        
                        # Update stats
                        if self.stage == 0:
                            player.vpip_count += 1
                else:
                    # Fold
                    player.has_folded = True
                    player.last_action = "Fold"
                    self.log_action(player, "Fold")
        else:
            # Post-flop play (simplified)
            if to_call == 0:
                if random.random() < adj_aggr * 0.5:
                    bet_amt = int(pot_size * random.uniform(0.33, 0.75))
                    bet_amt = min(bet_amt, player.chips)
                    if bet_amt > 0:
                        player.chips -= bet_amt
                        player.round_bet += bet_amt
                        self.pot += bet_amt
                        self.current_bet = player.round_bet
                        player.last_action = f"Bet ${bet_amt}"
                        self.log_action(player, "Bet", bet_amt)
                    else:
                        player.last_action = "Check"
                        self.log_action(player, "Check")
                else:
                    player.last_action = "Check"
                    self.log_action(player, "Check")
            else:
                if random.random() < adj_loose * 0.6:
                    if random.random() < adj_aggr * 0.4:
                        raise_amt = min(int(to_call * random.uniform(2, 3)), player.chips)
                        player.chips -= raise_amt
                        player.round_bet += raise_amt
                        self.pot += raise_amt
                        self.current_bet = player.round_bet
                        player.last_action = f"Raise ${raise_amt}"
                        self.log_action(player, "Raise", raise_amt)
                    else:
                        call_amt = min(to_call, player.chips)
                        player.chips -= call_amt
                        player.round_bet += call_amt
                        self.pot += call_amt
                        player.last_action = f"Call ${call_amt}"
                        self.log_action(player, "Call", call_amt)
                else:
                    player.has_folded = True
                    player.last_action = "Fold"
                    self.log_action(player, "Fold")

    def advance_turn(self):
        """Move to next active player"""
        num_p = len(self.players)
        original_idx = self.turn_index
        
        while True:
            self.turn_index = (self.turn_index + 1) % num_p
            if self.turn_index == original_idx:
                break
            if not self.players[self.turn_index].has_folded and self.players[self.turn_index].chips > 0:
                if self.players[self.turn_index].round_bet < self.current_bet:
                    self.turn_start_time = time.time()
                    return
        
        self.end_betting_round()

    def end_betting_round(self):
        """End current betting round"""
        # Reset round bets
        for p in self.players:
            p.round_bet = 0
        
        self.current_bet = 0
        
        # Check if only one player left
        active_count = sum(1 for p in self.players if not p.has_folded and p.chips > 0)
        if active_count <= 1:
            self.determine_winner()
            return
        
        # Move to next stage
        if self.stage == 0:  # Pre-flop -> Flop
            for _ in range(3):
                card = self.deck.pop()
                self.community.append(card)
            self.stage = 1
            self.top_status = "Flop"
            
        elif self.stage == 1:  # Flop -> Turn
            card = self.deck.pop()
            self.community.append(card)
            self.stage = 2
            self.top_status = "Turn"
            
        elif self.stage == 2:  # Turn -> River
            card = self.deck.pop()
            self.community.append(card)
            self.stage = 3
            self.top_status = "River"
            
        else:  # River -> Showdown
            self.determine_winner()
            return
        
        # Set first player after dealer
        num_p = len(self.players)
        self.turn_index = (self.dealer_index + 1) % num_p
        while self.players[self.turn_index].has_folded or self.players[self.turn_index].chips <= 0:
            self.turn_index = (self.turn_index + 1) % num_p
        
        self.turn_start_time = time.time()
        
        # Update training info
        if SHOW_EQUITY and not self.players[0].has_folded:
            active_opps = sum(1 for p in self.players[1:] if not p.has_folded)
            if active_opps > 0:
                equity = calculate_equity(self.players[0].hand, self.community, active_opps, iterations=500)
                self.equity_text = f"Your Equity: {equity*100:.1f}%"
        
        if SHOW_POT_ODDS:
            pot_odds, odds_text = self.calculate_pot_odds()
            self.pot_odds_text = odds_text

    def process_turn(self):
        """Process current turn (bot or timer)"""
        if self.stage >= 4:
            return
        
        current_player = self.players[self.turn_index]
        
        if current_player.has_folded:
            self.advance_turn()
            return
        
        # Bot turn
        if not current_player.is_human and self.turn_index != 0:
            # Small delay for realism
            if time.time() - self.turn_start_time > random.uniform(0.5, 2.0):
                self.bot_act(self.turn_index)
                self.advance_turn()
        
        # Timer check
        if time.time() - self.turn_start_time > TURN_TIME_LIMIT:
            if self.turn_index == 0:
                # Auto-fold human if time runs out
                current_player.has_folded = True
                current_player.last_action = "Fold (Timeout)"
                self.log_action(current_player, "Fold (Timeout)")
            self.advance_turn()

    def determine_winner(self):
        """Determine the winner of the hand"""
        active_hands = []
        for player in self.players:
            if not player.has_folded:
                full_hand = player.hand + self.community
                score, tie_list, hand_name = evaluate_hand(full_hand)
                active_hands.append((score, tie_list, player, hand_name))
                
                # Reveal bot cards for showdown
                if not player.is_human:
                    for c in player.hand:
                        c.is_face_up = True
        
        if len(active_hands) == 0:
            self.msg = "No active players!"
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
                
                # Update showdown stats
                w.showdowns_won += 1
                w.showdowns_seen += 1
            
            # Update showdown seen for losers
            for entry in active_hands:
                if entry[2] not in winners:
                    entry[2].showdowns_seen += 1
            
            names = " & ".join([w.name for w in winners])
            self.msg = f"Winner: {names} +${prize}"
        
        self.stage = 4
        self.top_status = "Round Over"
        self.buttons = [self.btn_next]
        self.btn_next.active = True
        self.input_box.active = False
        
        # Save hand history
        self.save_hand_history()

    def draw_training_panel(self):
        """Draw training panel with advice and stats"""
        if not self.show_training_panel or self.turn_index != 0:
            return
        
        panel_x = WIDTH - 280
        panel_y = 100
        panel_w = 270
        panel_h = 400
        
        # Background
        pygame.draw.rect(screen, (10, 10, 30, 220), (panel_x, panel_y, panel_w, panel_h), border_radius=10)
        pygame.draw.rect(screen, WSOP_ACCENT, (panel_x, panel_y, panel_w, panel_h), 2, border_radius=10)
        
        # Title
        title = font_med.render("Training Mode", True, WSOP_ACCENT)
        screen.blit(title, (panel_x + 10, panel_y + 10))
        
        y_offset = panel_y + 50
        
        # Strategy Advice
        if SHOW_ADVICE and self.advice_text:
            advice_lines = self.advice_text.split('. ')
            for line in advice_lines:
                if line:
                    txt = font_small.render(line[:35], True, GREEN)
                    screen.blit(txt, (panel_x + 10, y_offset))
                    y_offset += 20
                    if len(line) > 35:
                        txt2 = font_small.render(line[35:], True, GREEN)
                        screen.blit(txt2, (panel_x + 10, y_offset))
                        y_offset += 20
        
        y_offset += 20
        
        # Equity
        if SHOW_EQUITY and self.equity_text and self.stage > 0:
            equity_txt = font_small.render(self.equity_text, True, YELLOW)
            screen.blit(equity_txt, (panel_x + 10, y_offset))
            y_offset += 25
            
            # Count outs
            if len(self.community) >= 3 and len(self.community) < 5:
                num_outs, outs_list = count_outs(self.players[0].hand, self.community)
                if num_outs > 0:
                    outs_txt = font_small.render(f"Outs: {num_outs}", True, YELLOW)
                    screen.blit(outs_txt, (panel_x + 10, y_offset))
                    y_offset += 20
        
        # Pot Odds
        if SHOW_POT_ODDS and self.pot_odds_text:
            lines = self.pot_odds_text.split('(')
            for i, line in enumerate(lines):
                if line:
                    display_line = line.replace(')', '')
                    txt = font_tiny.render(display_line[:40], True, WHITE)
                    screen.blit(txt, (panel_x + 10, y_offset))
                    y_offset += 18
        
        y_offset += 10
        
        # Position info
        pos_name = self.get_position_name(0)
        pos_txt = font_small.render(f"Position: {pos_name}", True, WSOP_ACCENT)
        screen.blit(pos_txt, (panel_x + 10, y_offset))
        y_offset += 25
        
        # Hand number
        hand_txt = font_tiny.render(f"Hand #{self.hand_number}", True, GRAY)
        screen.blit(hand_txt, (panel_x + 10, y_offset))

    def draw_hud(self, player, idx):
        """Draw HUD stats for a player"""
        if player.is_human:
            return
        
        hud_x = player.x
        hud_y = player.y + 110
        
        vpip = player.get_vpip()
        pfr = player.get_pfr()
        three_bet = player.get_3bet()
        
        hud_bg = pygame.Rect(hud_x - 5, hud_y, 140, 35)
        pygame.draw.rect(screen, (0, 0, 0, 180), hud_bg, border_radius=5)
        pygame.draw.rect(screen, (100, 100, 100), hud_bg, 1, border_radius=5)
        
        # VPIP
        vpip_color = GREEN if vpip < 30 else (YELLOW if vpip < 50 else RED)
        vpip_txt = font_hud.render(f"VPIP: {vpip}%", True, vpip_color)
        screen.blit(vpip_txt, (hud_x, hud_y + 2))
        
        # PFR
        pfr_color = GREEN if pfr < 25 else (YELLOW if pfr < 40 else RED)
        pfr_txt = font_hud.render(f"PFR: {pfr}%", True, pfr_color)
        screen.blit(pfr_txt, (hud_x + 70, hud_y + 2))
        
        # 3-bet
        if three_bet > 0:
            bet3_txt = font_hud.render(f"3B: {three_bet}%", True, WHITE)
            screen.blit(bet3_txt, (hud_x, hud_y + 17))
        
        # Hands played
        hands_txt = font_hud.render(f"n={player.total_hands}", True, GRAY)
        screen.blit(hands_txt, (hud_x + 70, hud_y + 17))

    def draw_win_label(self, player):
        """Draw win notification"""
        if player.win_desc:
            bx, by = player.bet_x, player.bet_y
            txt = font_win.render(player.win_desc, True, WSOP_ACCENT)
            txt_rect = txt.get_rect(center=(bx, by - 30))
            bg_rect = txt_rect.inflate(20, 10)
            pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect, border_radius=10)
            pygame.draw.rect(screen, WSOP_ACCENT, bg_rect, 2, border_radius=10)
            screen.blit(txt, txt_rect)

    def draw_markers(self, player, idx):
        """Draw dealer, SB, BB markers"""
        marker_y = player.y - 45
        marker_x = player.x - 20
        markers = []
        
        if idx == self.dealer_index:
            markers.append(("D", ORANGE_MARKER))
        
        num_p = len(self.players)
        sb_calc = (self.dealer_index + 1) % num_p
        while self.players[sb_calc].chips <= 0:
            sb_calc = (sb_calc + 1) % num_p
        if idx == sb_calc:
            markers.append(("SB", PURPLE_SB))
        
        bb_calc = (sb_calc + 1) % num_p
        while self.players[bb_calc].chips <= 0:
            bb_calc = (bb_calc + 1) % num_p
        if idx == bb_calc:
            markers.append(("BB", BLUE_BB))
        
        for text, color in markers:
            pygame.draw.circle(screen, color, (marker_x, marker_y), 15)
            pygame.draw.circle(screen, WHITE, (marker_x, marker_y), 15, 1)
            t_surf = font_small.render(text, True, WHITE)
            t_rect = t_surf.get_rect(center=(marker_x, marker_y))
            screen.blit(t_surf, t_rect)
            marker_x -= 35

    def draw_table_bet_and_status(self, player):
        """Draw bet amount and action status"""
        bx, by = player.bet_x, player.bet_y
        
        if player.round_bet > 0:
            bet_txt = font_bet_amount.render(f"${player.round_bet}", True, WSOP_ACCENT)
            screen.blit(bet_txt, (bx + 15, by - 10))
        
        if player.last_action:
            bg_color = GRAY
            if "Fold" in player.last_action:
                bg_color = RED_BTN
            elif "Bet" in player.last_action or "Raise" in player.last_action or "All-in" in player.last_action:
                bg_color = ORANGE_BTN
            elif "Check" in player.last_action:
                bg_color = WSOP_BLUE
            elif "Call" in player.last_action:
                bg_color = BLUE_BTN
            
            act_surf = font_small.render(player.last_action, True, WHITE)
            act_rect = act_surf.get_rect(center=(bx, by - 30))
            bg_rect = act_rect.inflate(10, 10)
            pygame.draw.rect(screen, bg_color, bg_rect, border_radius=5)
            screen.blit(act_surf, act_rect)

    def draw_table_background(self):
        """Draw poker table background"""
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
        """Main draw function"""
        self.draw_table_background()
        
        # Draw community cards
        comm_scale = 1.3
        comm_w = int(CARD_WIDTH * comm_scale)
        comm_start = WIDTH//2 - (2.5 * comm_w) - 10
        comm_y = HEIGHT//2 - 120 + 40
        for i, c in enumerate(self.community):
            c.draw(screen, comm_start + i * (comm_w + 5), comm_y, scale=comm_scale)
        
        # Draw players
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
            
            # Timer for current player
            if is_turn and not p.has_folded and self.stage < 4:
                time_elapsed = time.time() - self.turn_start_time
                time_left = max(0, TURN_TIME_LIMIT - time_elapsed)
                timer_str = f"{int(time_left)}s"
                timer_surf = font_timer.render(timer_str, True, TIMER_RED)
                screen.blit(timer_surf, (p.x + 135, p.y - 35))
            
            # Cards
            if p.has_folded:
                fold_txt = font_med.render("FOLD", True, RED)
                screen.blit(fold_txt, (p.x + 30, p.y + 40))
            elif p.is_active:
                for idx, card in enumerate(p.hand):
                    card.draw(screen, p.x + idx * (CARD_WIDTH + 5), p.y)
            
            # Markers and status
            self.draw_markers(p, i)
            self.draw_table_bet_and_status(p)
            self.draw_win_label(p)
            self.draw_hud(p, i)
        
        # Pot display
        pot_txt = font_large.render(f"POT: ${self.pot}", True, WSOP_ACCENT)
        pot_rect = pot_txt.get_rect(topright=(WIDTH - 300, 30))
        pygame.draw.rect(screen, (0, 0, 0, 150), pot_rect.inflate(20, 10), border_radius=10)
        pygame.draw.rect(screen, WSOP_BORDER, pot_rect.inflate(20, 10), 2, border_radius=10)
        screen.blit(pot_txt, pot_rect)
        
        # Status
        status_bg = pygame.Rect(20, 20, 350, 50)
        pygame.draw.rect(screen, (10, 10, 30), status_bg, border_radius=10)
        pygame.draw.rect(screen, WSOP_BORDER, status_bg, 2, border_radius=10)
        status_txt = font_med.render(self.top_status, True, WSOP_ACCENT)
        screen.blit(status_txt, (40, 32))
        
        # Buttons
        for btn in self.buttons:
            if btn.action_code != 4 or self.stage == 4:
                btn.draw(screen)
        
        # Input box
        if self.turn_index == 0 and self.stage < 4 and not self.players[0].has_folded:
            self.input_box.update()
            self.input_box.draw(screen)
        
        # Training panel
        self.draw_training_panel()
        
        pygame.display.flip()

# --- 6. Main Loop ---
game = PokerGame()
clock = pygame.time.Clock()
running = True

while running:
    game.process_turn()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        game.handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            
            if game.input_box and game.turn_index == 0:
                if game.input_box.rect.collidepoint(pos):
                    game.input_box.active = True
                else:
                    game.input_box.active = False
            
            for btn in game.buttons:
                if btn.is_clicked(pos):
                    if btn.action_code == 4:
                        game.start_new_hand()
                    else:
                        game.human_act(btn.action_code)
    
    game.draw()
    clock.tick(30)

pygame.quit()