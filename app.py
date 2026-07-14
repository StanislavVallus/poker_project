import streamlit as st
from engine import PokerEngine

# --- HELPER: MAKE CARDS LOOK NICE ---
def format_card(card_string):
    """Converts 'Ah' to 'A♥️', etc."""
    if not card_string:
        return "🎴"
    
    rank = card_string[0]
    suit = card_string[1]
    
    # Convert 'T' to '10' for visual preference
    if rank == 'T':
        rank = '10'
        
    suit_symbols = {"h": "♥️", "d": "♦️", "c": "♣️", "s": "♠️"}
    emoji = suit_symbols.get(suit, suit)
    
    return f"{rank}{emoji}"

# --- INITIALIZE THE GAME IN BROWSER MEMORY ---
if "game" not in st.session_state:
    # We import your exact backend engine here!
    st.session_state.game = PokerEngine(player_name="You", bot_name="Bot")
    st.session_state.game.start_new_hand()
    st.session_state.log = ["New hand dealt!"]

# Create a convenient variable to access the game state
game = st.session_state.game

# --- TEMPORARY DUMMY BOT LOGIC ---
def bot_make_move():
    """A basic bot that just calls/checks so you can test the UI."""
    bot = game.players[1]
    if bot.folded or game.current_street == "SHOWDOWN": 
        return
    
    # For now, the bot automatically calls whatever you bet
    action_desc = game.execute_action("call")
    st.session_state.log.insert(0, f"🤖 Bot: {action_desc}")
    
    # Check if the game reached showdown after the bot's call
    if game.current_street == "SHOWDOWN":
        winner, desc = game.get_winner()
        if winner:
            st.session_state.log.insert(0, f"🏆 {winner.name} wins with {desc}!")
        else:
            st.session_state.log.insert(0, f"🤝 Tie: {desc}")


# --- FRONTEND UI LAYOUT ---

# 1. Custom CSS for a Clean, Modern White UI
st.markdown(
    """
    <style>
    /* 1. Main Background and Global Text */
    .stApp {
        background-color: #ffffff;
    }
    
    /* Force text to be dark grey/black for high contrast on white */
    h1, h2, h3, p, span, div, label {
        color: #1f2937 !important;
    }
    
    /* 2. Button Styling */
    div.stButton > button {
        background-color: #f3f4f6;
        color: #1f2937 !important;
        border-radius: 8px;
        width: 100%;
        border: 1px solid #d1d5db;
        font-weight: 600;
        transition: 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        background-color: #e5e7eb;
        border-color: #9ca3af;
    }
    
    /* 3. Metric Text Styling (Total Pot Container) */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); /* Adds a very soft shadow */
    }
    
    /* Targets the Label ("TOTAL POT") */
    div[data-testid="metric-container"] > label[data-testid="stMetricLabel"] > div {
        color: #6b7280 !important; /* Muted grey for the label */
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Targets the Value (e.g., "$30") */
    div[data-testid="metric-container"] > div[data-testid="stMetricValue"] > div {
        color: #2563eb !important; /* A sharp, highly visible royal blue for the money */
        font-weight: 900; 
    }
    
    /* Lighten the standard Streamlit horizontal dividers */
    hr {
        border-bottom-color: #e5e7eb !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🃏 Python Poker Table")
st.write("---")

# 2. Table Info
st.metric(label="💰 TOTAL POT", value=f"${game.pot}")
st.caption(f"Current Street: **{game.current_street}**")

# 3. Community Cards
st.subheader("🃏 Community Cards")
comm_formatted = [format_card(c) for c in game.community_cards]

# Pad the display with hidden cards so it always shows 5 slots
while len(comm_formatted) < 5:
    comm_formatted.append("🎴")
st.info(f"**[ {' | '.join(comm_formatted)} ]**")

st.write("---")

# 4. Player & Bot Hands
col1, col2 = st.columns(2)
player = game.players[0]
bot = game.players[1]

with col1:
    st.subheader("🧑 Your Hand")
    hand_formatted = [format_card(c) for c in player.hand]
    st.success(f"**[ {' | '.join(hand_formatted)} ]**\n\nChips: ${player.chips} | Current Bet: ${player.current_bet}")

with col2:
    st.subheader("🤖 Bot Hand")
    # Only reveal bot cards if the game is over or player folded
    if game.current_street == "SHOWDOWN" or player.folded:
        bot_hand = [format_card(c) for c in bot.hand]
        st.error(f"**[ {' | '.join(bot_hand)} ]**\n\nChips: ${bot.chips} | Current Bet: ${bot.current_bet}")
    else:
        st.error(f"**[ 🎴 | 🎴 ]**\n\nChips: ${bot.chips} | Current Bet: ${bot.current_bet}")

st.write("---")

# 5. User Controls (Buttons)
current_actor = game.players[game.current_actor_index]

# If the hand is still going and it's your turn:
if game.current_street != "SHOWDOWN":
    if current_actor.name == "You":
        st.subheader("Your Action:")
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        
        with btn_col1:
            if st.button("Fold 🏳️"):
                desc = game.execute_action("fold")
                st.session_state.log.insert(0, f"🧑 You: {desc}")
                st.rerun() # Refresh the page instantly
                
        with btn_col2:
            to_call = game.current_bet - player.current_bet
            label = "Check ✊" if to_call == 0 else f"Call ${to_call} 📞"
            
            if st.button(label):
                desc = game.execute_action("call")
                st.session_state.log.insert(0, f"🧑 You: {desc}")
                
                # If your call didn't end the round, trigger the bot
                if game.players[game.current_actor_index].name == "Bot":
                    bot_make_move()
                st.rerun()
                
        with btn_col3:
            raise_amt = st.number_input("Raise Amount", min_value=10, max_value=player.chips, step=10, value=20)
            if st.button("Raise 📈"):
                desc = game.execute_action("raise", raise_amount=raise_amt)
                st.session_state.log.insert(0, f"🧑 You: {desc}")
                
                # Trigger bot to answer your raise
                if game.players[game.current_actor_index].name == "Bot":
                    bot_make_move()
                st.rerun()
    else:
        st.warning("Waiting for Bot...")
        # A manual trigger just in case the bot acts first on a street
        if st.button("Trigger Bot Move"):
            bot_make_move()
            st.rerun()
            
# If the hand is over:
else:
    st.subheader("🏁 Hand Complete")
    if st.button("Deal Next Hand 🔄"):
        game.start_new_hand()
        st.session_state.log.insert(0, "--- NEW HAND ---")
        st.rerun()

st.write("---")

# 6. Action Log
st.caption("Action Log (Latest first):")
for entry in st.session_state.log[:8]:
    st.markdown(f"> *{entry}*")