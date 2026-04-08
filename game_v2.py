import pygame
import random
from collections import Counter

# 初始化
pygame.init()
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("德州扑克 Texas Hold'em")

# 颜色方案 - 现代扁平设计
BG_COLOR = (26, 35, 126)  # 深蓝背景
TABLE_COLOR = (16, 124, 16)  # 绿色桌面
CARD_BG = (255, 255, 255)
CARD_BORDER = (220, 220, 220)
BTN_PRIMARY = (33, 150, 243)  # 蓝色按钮
BTN_DANGER = (244, 67, 54)  # 红色按钮
BTN_SUCCESS = (76, 175, 80)  # 绿色按钮
BTN_WARNING = (255, 152, 0)  # 橙色按钮
TEXT_DARK = (33, 33, 33)
TEXT_LIGHT = (255, 255, 255)
GOLD = (255, 193, 7)
DEALER_COLOR = (255, 87, 34)

# 字体
font_large = pygame.font.SysFont("arial", 36, bold=True)
font_medium = pygame.font.SysFont("arial", 24, bold=True)
font_small = pygame.font.SysFont("arial", 18, bold=True)
font_card = pygame.font.SysFont("arial", 32, bold=True)
font_suit = pygame.font.SysFont("segoeuisymbol", 28)

# 游戏参数
CARD_WIDTH, CARD_HEIGHT = 70, 100
INITIAL_CHIPS = 1000
SMALL_BLIND = 10
BIG_BLIND = 20

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUES = {r: i for i, r in enumerate(RANKS, 2)}

# 牌类
class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.value = RANK_VALUES[rank]
    
    def draw(self, surface, x, y, face_down=False):
        # 卡片背景
        card_rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        pygame.draw.rect(surface, CARD_BG, card_rect, border_radius=8)
        pygame.draw.rect(surface, CARD_BORDER, card_rect, 3, border_radius=8)
        
        if face_down:
            # 背面图案
            pygame.draw.rect(surface, BTN_PRIMARY, card_rect.inflate(-10, -10), border_radius=5)
            return
        
        # 花色颜色
        color = (220, 20, 60) if self.suit in ['♥', '♦'] else TEXT_DARK
        
        # 显示点数
        rank_surf = font_card.render(self.rank, True, color)
        surface.blit(rank_surf, (x + 8, y + 5))
        
        # 显示花色
        suit_surf = font_suit.render(self.suit, True, color)
        surface.blit(suit_surf, (x + CARD_WIDTH - 25, y + 5))
        
        # 底部倒置显示
        rank_surf_flip = pygame.transform.rotate(rank_surf, 180)
        surface.blit(rank_surf_flip, (x + CARD_WIDTH - rank_surf.get_width() - 8, 
                                       y + CARD_HEIGHT - rank_surf.get_height() - 5))
        suit_surf_flip = pygame.transform.rotate(suit_surf, 180)
        surface.blit(suit_surf_flip, (x + 5, y + CARD_HEIGHT - suit_surf.get_height() - 5))

# 按钮类
class Button:
    def __init__(self, x, y, width, height, text, color, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = tuple(min(c + 30, 255) for c in color)
        self.action = action
        self.enabled = True
    
    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.rect.collidepoint(mouse_pos) and self.enabled
        
        color = self.hover_color if is_hover else self.color
        if not self.enabled:
            color = (100, 100, 100)
        
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, TEXT_LIGHT, self.rect, 2, border_radius=8)
        
        text_surf = font_medium.render(self.text, True, TEXT_LIGHT)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos) and self.enabled

# 玩家类
class Player:
    def __init__(self, name, chips, x, y, is_human=False):
        self.name = name
        self.chips = chips
        self.hand = []
        self.x = x
        self.y = y
        self.is_human = is_human
        self.folded = False
        self.bet = 0
        self.total_bet = 0
        self.last_action = ""
    
    def reset_for_hand(self):
        self.hand = []
        self.folded = False
        self.bet = 0
        self.total_bet = 0
        self.last_action = ""

# 牌力评估
def evaluate_hand(cards):
    if len(cards) < 5:
        return (0, [], "高牌")
    
    values = sorted([c.value for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    
    # 统计
    value_counts = Counter(values)
    suit_counts = Counter(suits)
    
    # 同花
    is_flush = max(suit_counts.values()) >= 5
    
    # 顺子检测
    def check_straight(vals):
        unique = sorted(set(vals), reverse=True)
        # A-5特殊顺子
        if {14, 5, 4, 3, 2}.issubset(set(unique)):
            return 5
        for i in range(len(unique) - 4):
            if unique[i] - unique[i + 4] == 4:
                return unique[i]
        return None
    
    straight_high = check_straight(values)
    
    # 同花顺
    if is_flush and straight_high:
        return (8, [straight_high], "同花顺")
    
    # 四条
    fours = [v for v, c in value_counts.items() if c == 4]
    if fours:
        return (7, [fours[0]], "四条")
    
    # 葫芦
    threes = [v for v, c in value_counts.items() if c == 3]
    pairs = [v for v, c in value_counts.items() if c == 2]
    if threes and (len(threes) > 1 or pairs):
        return (6, [max(threes)], "葫芦")
    
    # 同花
    if is_flush:
        return (5, values[:5], "同花")
    
    # 顺子
    if straight_high:
        return (4, [straight_high], "顺子")
    
    # 三条
    if threes:
        return (3, [max(threes)], "三条")
    
    # 两对
    if len(pairs) >= 2:
        top_pairs = sorted(pairs, reverse=True)[:2]
        return (2, top_pairs, "两对")
    
    # 一对
    if pairs:
        return (1, [pairs[0]], "一对")
    
    return (0, values[:5], "高牌")

# 德州扑克游戏
class TexasHoldem:
    def __init__(self):
        # 创建玩家（4人桌）
        positions = [
            (WIDTH // 2 - 80, HEIGHT - 180),  # 玩家（底部）
            (100, HEIGHT // 2 - 50),  # 左侧
            (WIDTH // 2 - 80, 100),  # 顶部
            (WIDTH - 220, HEIGHT // 2 - 50)  # 右侧
        ]
        
        self.players = [
            Player("你", INITIAL_CHIPS, positions[0][0], positions[0][1], True),
            Player("Andy", INITIAL_CHIPS, positions[1][0], positions[1][1]),
            Player("Tom", INITIAL_CHIPS, positions[2][0], positions[2][1]),
            Player("Sarah", INITIAL_CHIPS, positions[3][0], positions[3][1])
        ]
        
        self.deck = []
        self.community = []
        self.pot = 0
        self.current_bet = 0
        self.dealer_pos = 0
        self.current_player = 0
        self.stage = 0  # 0=preflop, 1=flop, 2=turn, 3=river, 4=showdown
        self.stage_names = ["翻牌前", "翻牌", "转牌", "河牌", "摊牌"]
        
        # 按钮
        btn_y = HEIGHT - 100
        btn_spacing = 140
        start_x = WIDTH // 2 - btn_spacing * 2
        
        self.buttons = [
            Button(start_x, btn_y, 120, 50, "弃牌", BTN_DANGER, "fold"),
            Button(start_x + btn_spacing, btn_y, 120, 50, "跟注", BTN_PRIMARY, "call"),
            Button(start_x + btn_spacing * 2, btn_y, 120, 50, "加注", BTN_WARNING, "raise"),
            Button(start_x + btn_spacing * 3, btn_y, 120, 50, "全下", BTN_SUCCESS, "allin")
        ]
        
        self.new_hand_button = Button(WIDTH - 200, HEIGHT - 60, 180, 50, 
                                      "开始新局", BTN_SUCCESS, "newhand")
        
        self.message = ""
        self.winner_message = ""
        self.start_new_hand()
    
    def create_deck(self):
        deck = []
        for suit in SUITS:
            for rank in RANKS:
                deck.append(Card(suit, rank))
        random.shuffle(deck)
        return deck
    
    def start_new_hand(self):
        # 重置
        for p in self.players:
            p.reset_for_hand()
        
        self.deck = self.create_deck()
        self.community = []
        self.pot = 0
        self.current_bet = 0
        self.stage = 0
        self.message = ""
        self.winner_message = ""
        
        # 发牌
        for _ in range(2):
            for p in self.players:
                if p.chips > 0:
                    p.hand.append(self.deck.pop())
        
        # 盲注
        self.dealer_pos = (self.dealer_pos + 1) % len(self.players)
        sb_pos = (self.dealer_pos + 1) % len(self.players)
        bb_pos = (self.dealer_pos + 2) % len(self.players)
        
        # 下盲注
        self.players[sb_pos].bet = min(SMALL_BLIND, self.players[sb_pos].chips)
        self.players[sb_pos].chips -= self.players[sb_pos].bet
        self.players[bb_pos].bet = min(BIG_BLIND, self.players[bb_pos].chips)
        self.players[bb_pos].chips -= self.players[bb_pos].bet
        
        self.pot = self.players[sb_pos].bet + self.players[bb_pos].bet
        self.current_bet = BIG_BLIND
        self.current_player = (bb_pos + 1) % len(self.players)
        
        self.message = f"{self.stage_names[self.stage]} - 轮到 {self.players[self.current_player].name}"
    
    def player_action(self, action, raise_amount=0):
        player = self.players[self.current_player]
        
        if action == "fold":
            player.folded = True
            player.last_action = "弃牌"
        
        elif action == "call":
            call_amount = min(self.current_bet - player.bet, player.chips)
            player.chips -= call_amount
            player.bet += call_amount
            self.pot += call_amount
            player.last_action = f"跟注 ${call_amount}"
        
        elif action == "raise":
            if raise_amount == 0:
                raise_amount = self.current_bet * 2
            total_bet = min(raise_amount, player.chips + player.bet)
            to_call = self.current_bet - player.bet
            raise_by = total_bet - self.current_bet
            
            amount_to_pay = min(to_call + raise_by, player.chips)
            player.chips -= amount_to_pay
            player.bet += amount_to_pay
            self.pot += amount_to_pay
            self.current_bet = player.bet
            player.last_action = f"加注至 ${player.bet}"
        
        elif action == "allin":
            all_in_amount = player.chips
            player.chips = 0
            player.bet += all_in_amount
            self.pot += all_in_amount
            if player.bet > self.current_bet:
                self.current_bet = player.bet
            player.last_action = f"全下 ${all_in_amount}"
        
        # 下一个玩家
        self.next_player()
    
    def next_player(self):
        # 找下一个活跃玩家
        start_pos = self.current_player
        while True:
            self.current_player = (self.current_player + 1) % len(self.players)
            
            # 检查是否回到起点（一轮结束）
            if self.current_player == start_pos or self.check_betting_round_complete():
                self.advance_stage()
                return
            
            player = self.players[self.current_player]
            if not player.folded and player.chips > 0:
                self.message = f"{self.stage_names[self.stage]} - 轮到 {player.name}"
                
                # AI行动
                if not player.is_human:
                    pygame.time.wait(500)
                    self.ai_decision(player)
                return
    
    def check_betting_round_complete(self):
        # 检查所有活跃玩家是否已匹配最高下注
        active_players = [p for p in self.players if not p.folded and p.chips > 0]
        if len(active_players) <= 1:
            return True
        
        max_bet = max(p.bet for p in self.players)
        for p in active_players:
            if p.bet < max_bet:
                return False
        return True
    
    def advance_stage(self):
        # 重置下注
        for p in self.players:
            p.total_bet += p.bet
            p.bet = 0
        
        self.current_bet = 0
        self.stage += 1
        
        if self.stage == 1:  # Flop
            self.community.extend([self.deck.pop(), self.deck.pop(), self.deck.pop()])
        elif self.stage == 2:  # Turn
            self.community.append(self.deck.pop())
        elif self.stage == 3:  # River
            self.community.append(self.deck.pop())
        elif self.stage >= 4:  # Showdown
            self.showdown()
            return
        
        # 从庄家后开始
        self.current_player = (self.dealer_pos + 1) % len(self.players)
        while self.players[self.current_player].folded or self.players[self.current_player].chips == 0:
            self.current_player = (self.current_player + 1) % len(self.players)
        
        self.message = f"{self.stage_names[self.stage]} - 轮到 {self.players[self.current_player].name}"
        
        # AI玩家自动行动
        if not self.players[self.current_player].is_human:
            pygame.time.wait(500)
            self.ai_decision(self.players[self.current_player])
    
    def ai_decision(self, player):
        # 简化的AI逻辑
        hand_strength = self.evaluate_hand_strength(player)
        
        # 根据牌力决定
        if hand_strength < 0.3:
            if self.current_bet == 0:
                self.player_action("call")
            else:
                self.player_action("fold")
        elif hand_strength < 0.6:
            self.player_action("call")
        else:
            if random.random() < 0.7:
                self.player_action("raise")
            else:
                self.player_action("call")
    
    def evaluate_hand_strength(self, player):
        # 简单评估牌力（0-1）
        all_cards = player.hand + self.community
        if not all_cards:
            return 0.3
        
        rank, _, name = evaluate_hand(all_cards)
        
        # 基础牌力
        strength_map = {
            8: 0.99, 7: 0.95, 6: 0.90,  # 同花顺、四条、葫芦
            5: 0.80, 4: 0.70, 3: 0.60,  # 同花、顺子、三条
            2: 0.50, 1: 0.35, 0: 0.20   # 两对、一对、高牌
        }
        
        return strength_map.get(rank, 0.3)
    
    def showdown(self):
        active = [p for p in self.players if not p.folded]
        
        if len(active) == 1:
            winner = active[0]
            winner.chips += self.pot
            self.winner_message = f"{winner.name} 赢得 ${self.pot}!"
        else:
            # 比牌
            best_rank = -1
            winners = []
            
            for p in active:
                rank, kickers, name = evaluate_hand(p.hand + self.community)
                p.hand_rank = (rank, kickers, name)
                
                if rank > best_rank:
                    best_rank = rank
                    winners = [p]
                elif rank == best_rank:
                    # 比较踢脚牌
                    if kickers > winners[0].hand_rank[1]:
                        winners = [p]
                    elif kickers == winners[0].hand_rank[1]:
                        winners.append(p)
            
            # 分配底池
            share = self.pot // len(winners)
            for w in winners:
                w.chips += share
            
            winner_names = ", ".join([w.name for w in winners])
            hand_name = winners[0].hand_rank[2]
            self.winner_message = f"{winner_names} 以 {hand_name} 赢得 ${share}!"
        
        self.stage = 4
    
    def draw(self):
        # 背景
        screen.fill(BG_COLOR)
        
        # 桌面
        table_rect = pygame.Rect(150, 150, WIDTH - 300, HEIGHT - 350)
        pygame.draw.ellipse(screen, TABLE_COLOR, table_rect)
        pygame.draw.ellipse(screen, GOLD, table_rect, 5)
        
        # 底池
        pot_text = font_large.render(f"底池: ${self.pot}", True, GOLD)
        pot_rect = pot_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(pot_text, pot_rect)
        
        # 公共牌
        if self.community:
            comm_x = WIDTH // 2 - (len(self.community) * (CARD_WIDTH + 10)) // 2
            comm_y = HEIGHT // 2 + 50
            for i, card in enumerate(self.community):
                card.draw(screen, comm_x + i * (CARD_WIDTH + 10), comm_y)
        
        # 玩家信息
        for i, player in enumerate(self.players):
            # 背景框
            info_rect = pygame.Rect(player.x - 10, player.y - 60, 180, 50)
            color = GOLD if i == self.dealer_pos else TEXT_LIGHT
            pygame.draw.rect(screen, (0, 0, 0, 150), info_rect, border_radius=8)
            pygame.draw.rect(screen, color, info_rect, 2, border_radius=8)
            
            # 名字和筹码
            name_color = TEXT_LIGHT if not player.folded else (150, 150, 150)
            name_text = font_small.render(f"{player.name}: ${player.chips}", True, name_color)
            screen.blit(name_text, (player.x, player.y - 50))
            
            # 当前下注
            if player.bet > 0:
                bet_text = font_small.render(f"${player.bet}", True, GOLD)
                screen.blit(bet_text, (player.x, player.y - 30))
            
            # 庄家标记
            if i == self.dealer_pos:
                dealer_surf = font_small.render("D", True, TEXT_DARK)
                dealer_rect = pygame.Rect(player.x + 160, player.y - 50, 30, 30)
                pygame.draw.circle(screen, DEALER_COLOR, dealer_rect.center, 15)
                screen.blit(dealer_surf, (dealer_rect.x + 8, dealer_rect.y + 5))
            
            # 手牌
            if player.folded:
                fold_text = font_medium.render("已弃牌", True, BTN_DANGER)
                screen.blit(fold_text, (player.x + 20, player.y + 30))
            else:
                for j, card in enumerate(player.hand):
                    face_down = not player.is_human and self.stage < 4
                    card.draw(screen, player.x + j * (CARD_WIDTH + 10), player.y, face_down)
            
            # 上一个动作
            if player.last_action:
                action_text = font_small.render(player.last_action, True, TEXT_LIGHT)
                screen.blit(action_text, (player.x, player.y + 110))
        
        # 消息
        if self.message:
            msg_surf = font_medium.render(self.message, True, TEXT_LIGHT)
            msg_rect = msg_surf.get_rect(center=(WIDTH // 2, 50))
            pygame.draw.rect(screen, (0, 0, 0, 200), msg_rect.inflate(40, 20), border_radius=10)
            screen.blit(msg_surf, msg_rect)
        
        # 赢家消息
        if self.winner_message:
            win_surf = font_large.render(self.winner_message, True, GOLD)
            win_rect = win_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))
            pygame.draw.rect(screen, (0, 0, 0, 200), win_rect.inflate(40, 20), border_radius=10)
            screen.blit(win_surf, win_rect)
        
        # 按钮
        if self.stage < 4 and self.current_player == 0 and not self.players[0].folded:
            for btn in self.buttons:
                # 启用/禁用按钮
                if btn.action == "call":
                    btn.enabled = self.current_bet > self.players[0].bet
                    if btn.enabled:
                        call_amount = self.current_bet - self.players[0].bet
                        btn.text = f"跟注 ${call_amount}"
                    else:
                        btn.text = "过牌"
                elif btn.action == "raise":
                    btn.enabled = self.players[0].chips > self.current_bet - self.players[0].bet
                elif btn.action == "allin":
                    btn.enabled = self.players[0].chips > 0
                
                btn.draw(screen)
        
        # 新局按钮
        if self.stage >= 4:
            self.new_hand_button.draw(screen)
        
        pygame.display.flip()
    
    def handle_click(self, pos):
        # 处理按钮点击
        if self.stage < 4 and self.current_player == 0 and not self.players[0].folded:
            for btn in self.buttons:
                if btn.is_clicked(pos):
                    if btn.action == "call" and self.current_bet == self.players[0].bet:
                        self.player_action("call")  # 过牌
                    else:
                        self.player_action(btn.action)
                    return
        
        if self.stage >= 4:
            if self.new_hand_button.is_clicked(pos):
                self.start_new_hand()

# 主循环
def main():
    game = TexasHoldem()
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                game.handle_click(event.pos)
        
        game.draw()
        clock.tick(30)
    
    pygame.quit()

if __name__ == "__main__":
    main()