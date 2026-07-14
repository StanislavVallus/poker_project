import random
from treys import Card, Evaluator

SUITS = ["h", "d", "c", "s"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]


class Player:

    def __init__(self, name: str, chips: int = 1000):
        self.name = name
        self.chips = chips
        self.hand = []
        self.current_bet = 0  # Chips committed in the current street
        self.folded = False
        self.is_bot = "bot" in name.lower()

    def reset_for_new_hand(self):
        self.hand = []
        self.current_bet = 0
        self.folded = False

    def __repr__(self):
        return f"{self.name} (${self.chips}) | Hand: {self.hand} | Street Bet: ${self.current_bet}"


class PokerEngine:

    def __init__(self, player_name="Player", bot_name="Bot"):
        self.players = [Player(player_name), Player(bot_name)]
        self.deck = []
        self.community_cards = []
        self.pot = 0
        self.current_street = "PREFLOP"

        self.button_index = 0  # 0 = Player, 1 = Bot
        self.small_blind = 10
        self.big_blind = 20

        self.current_bet = 0  # The highest individual bet on the current street
        self.current_actor_index = 0
        self.last_aggressor_index = (
            None  # Tracks who made the last aggressive action (raise)
        )
        self.street_action_count = 0  # Counts how many actions occurred on this street

        self.evaluator = Evaluator()

    def create_deck(self):
        self.deck = [f"{rank}{suit}" for rank in RANKS for suit in SUITS]
        random.shuffle(self.deck)

    def start_new_hand(self):
        self.create_deck()
        self.community_cards = []
        self.pot = 0
        self.current_street = "PREFLOP"
        self.last_aggressor_index = None
        self.street_action_count = 0

        for p in self.players:
            p.reset_for_new_hand()

        self.button_index = 1 - self.button_index

        sb_player = self.players[self.button_index]
        bb_player = self.players[1 - self.button_index]

        # Deduct blinds
        sb_player.chips -= self.small_blind
        sb_player.current_bet = self.small_blind

        bb_player.chips -= self.big_blind
        bb_player.current_bet = self.big_blind

        self.pot = self.small_blind + self.big_blind
        self.current_bet = self.big_blind

        # In heads-up, SB (button) acts first pre-flop
        self.current_actor_index = self.button_index

        for player in self.players:
            player.hand = [self.deck.pop(), self.deck.pop()]

    def advance_street(self):
        """Prepares the table state for the next card dealing round."""
        # Reset street betting trackers
        for p in self.players:
            p.current_bet = 0
        self.current_bet = 0
        self.last_aggressor_index = None
        self.street_action_count = 0

        # In Heads-Up, BB position acts first on flop, turn, and river
        self.current_actor_index = 1 - self.button_index

        if self.current_street == "PREFLOP":
            self.current_street = "FLOP"
            self.deck.pop()
            self.community_cards = [self.deck.pop() for _ in range(3)]
        elif self.current_street == "FLOP":
            self.current_street = "TURN"
            self.deck.pop()
            self.community_cards.append(self.deck.pop())
        elif self.current_street == "TURN":
            self.current_street = "RIVER"
            self.deck.pop()
            self.community_cards.append(self.deck.pop())
        elif self.current_street == "RIVER":
            self.current_street = "SHOWDOWN"

    # --- NEW: SUBTASK 4 BETTING LOGIC ---

    def execute_action(self, action: str, raise_amount: int = 0):
        """Processes a player's move.

        Actions: 'fold', 'call' (or check), 'raise'
        """
        actor = self.players[self.current_actor_index]
        opponent = self.players[1 - self.current_actor_index]

        self.street_action_count += 1

        if action == "fold":
            actor.folded = True
            self.current_street = "SHOWDOWN"
            return f"{actor.name} folds!"

        elif action == "call":
            # If the current bet is equal to actor's bet, it's a "Check"
            to_call = self.current_bet - actor.current_bet

            if to_call == 0:
                action_desc = f"{actor.name} checks."
            else:
                # Ensure they don't bet more chips than they have (All-in limit)
                to_call = min(to_call, actor.chips)
                actor.chips -= to_call
                actor.current_bet += to_call
                self.pot += to_call
                action_desc = f"{actor.name} calls ${to_call}."

            # Check if this closes the betting round
            self.evaluate_betting_round_end()
            return action_desc

        elif action == "raise":
            # In poker, a raise must be at least twice the current bet level
            # We will calculate total target bet level
            current_contrib = actor.current_bet
            to_call = self.current_bet - current_contrib
            total_raise_cost = to_call + raise_amount

            # Cap raise cost by player's remaining chip stack
            total_raise_cost = min(total_raise_cost, actor.chips)

            actor.chips -= total_raise_cost
            actor.current_bet += total_raise_cost
            self.pot += total_raise_cost

            # Set the new table bet benchmark
            self.current_bet = actor.current_bet
            self.last_aggressor_index = self.current_actor_index

            # Pass turn to the other player
            self.current_actor_index = 1 - self.current_actor_index
            return f"{actor.name} raises by ${raise_amount} (total bet: ${self.current_bet})."

    def evaluate_betting_round_end(self):
        """Checks if both players have acted and their bets are equal."""
        p1, p2 = self.players[0], self.players[1]

        # Betting round is complete if:
        # 1. Both players have acted at least once, AND
        # 2. Their street bets are equal (and neither has folded)
        if self.street_action_count >= 2 and p1.current_bet == p2.current_bet:
            self.advance_street()
        else:
            # Shift action to the next player
            self.current_actor_index = 1 - self.current_actor_index

    def get_winner(self):
        active_players = [p for p in self.players if not p.folded]
        if len(active_players) == 1:
            return active_players[0], "Default (Opponent Folded)"

        treys_board = [Card.new(c) for c in self.community_cards]
        scores = []
        for player in active_players:
            treys_hand = [Card.new(c) for c in player.hand]
            score = self.evaluator.evaluate(treys_board, treys_hand)
            scores.append((player, score))

        scores.sort(key=lambda x: x[1])
        winner, winning_score = scores[0]
        rank_class = self.evaluator.get_rank_class(winning_score)
        hand_description = self.evaluator.class_to_string(rank_class)

        if len(scores) > 1 and scores[0][1] == scores[1][1]:
            return None, f"Split Pot (Both have {hand_description})"

        return winner, hand_description


# --- RUNNING A SIMULATED GAME ROUND ---
if __name__ == "__main__":
    game = PokerEngine()
    game.start_new_hand()

    print("--- PREFLOP ---")
    print(game.players[0])
    print(game.players[1])
    print(f"Current Actor: {game.players[game.current_actor_index].name}")

    # Player 1 (Dealer) Calls
    print("\nAction 1:")
    print(game.execute_action("call"))

    # Player 2 (Big Blind) Checks (Closing the Pre-flop)
    print("\nAction 2:")
    print(game.execute_action("call"))

    print(f"\n--- Street Advanced to: {game.current_street} ---")
    print(f"Community cards: {game.community_cards}")
    print(f"Pot: ${game.pot}")
    print(f"Current Actor: {game.players[game.current_actor_index].name}")

    # Player 1 bets/raises on the Flop
    print("\nAction 3:")
    print(game.execute_action("raise", raise_amount=50))

    # Player 2 Calls the flop bet
    print("\nAction 4:")
    print(game.execute_action("call"))

    print(f"\n--- Street Advanced to: {game.current_street} ---")
    print(f"Community cards: {game.community_cards}")
    print(f"Pot: ${game.pot}")