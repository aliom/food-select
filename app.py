import streamlit as st
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
import time
import random
import uuid

# ==============================================================================
# 1. 配置与数据库层
# ==============================================================================

st.set_page_config(page_title="Balatro Eats", page_icon="🃏", layout="wide")

# 保持使用 V5 数据库
DB_FILE = "sqlite:///local_poker_v5.sqlite"
MAX_CARDS_PER_USER = 3
COLOR_PALETTE = [
    "#FF4500", "#00BFFF", "#32CD32", "#FFD700", 
    "#FF00FF", "#00FFFF", "#FF1493", "#FFA500"
]

def get_db_url():
    try:
        if "db_url" in st.secrets:
            return st.secrets["db_url"]
    except Exception:
        pass
    return DB_FILE

engine = create_engine(get_db_url(), connect_args={"check_same_thread": False} if "sqlite" in get_db_url() else {})
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()

# --- Models ---
class Room(Base):
    __tablename__ = "rooms"
    id = Column(String, primary_key=True, index=True)
    host_name = Column(String)
    status = Column(String, default="WAITING") 
    winner_text = Column(String, nullable=True)
    last_updated = Column(String)

class RoomUser(Base):
    __tablename__ = "room_users"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, index=True)
    user_token = Column(String, index=True)
    nickname = Column(String)
    color_hex = Column(String)

class CardOption(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, index=True)
    text = Column(String)
    creator = Column(String)
    user_token = Column(String)
    tilt_seed = Column(Integer, default=0)

Base.metadata.create_all(bind=engine)

def get_user_color(db, room_id, user_token, nickname):
    user_record = db.query(RoomUser).filter(RoomUser.room_id == room_id, RoomUser.user_token == user_token).first()
    if user_record:
        return user_record.color_hex
    used_colors = [u.color_hex for u in db.query(RoomUser).filter(RoomUser.room_id == room_id).all()]
    available = [c for c in COLOR_PALETTE if c not in used_colors]
    assigned_color = available[0] if available else random.choice(COLOR_PALETTE)
    new_user = RoomUser(room_id=room_id, user_token=user_token, nickname=nickname, color_hex=assigned_color)
    db.add(new_user)
    db.commit()
    return assigned_color

# ==============================================================================
# 2. 视觉风格 (纯净版 CSS)
# ==============================================================================

def inject_balatro_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap');

        /* 全局背景 */
        .stApp {
            background-color: #2C2C2C;
            background-image: radial-gradient(circle at center, #3a3a3a 0%, #1a1a1a 100%);
            color: #E0E0E0;
            font-family: 'VT323', monospace;
        }
        header, footer {visibility: hidden;}
        
        /* CRT 扫描线 */
        .crt-overlay {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), 
                        linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
            background-size: 100% 2px, 3px 100%;
            pointer-events: none; z-index: 9999;
        }

        .glitch-title {
            font-family: 'Press Start 2P', cursive;
            color: #FF4500; text-shadow: 2px 2px #00BFFF;
            text-align: center; font-size: 3em !important; margin-bottom: 20px;
        }

        /* --- 卡片样式 --- */
        .poker-card {
            background-color: #f0f0f0;
            border: 4px solid #1a1a1a;
            border-radius: 8px;
            padding: 10px;
            text-align: center;
            box-shadow: 4px 4px 0px #000;
            transition: all 0.2s ease;
            color: #1a1a1a;
            position: relative;
            height: 180px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            margin-bottom: 10px; /* 给下方按钮留出空间 */
        }
        
        .card-back-pattern {
            background-color: #333;
            background-image: repeating-linear-gradient(45deg, #444 0px, #444 10px, #333 10px, #333 20px);
            height: 100%; width: 100%;
            border: 2px solid #fff;
            display: flex; align-items: center; justify-content: center;
            color: #fff; font-family: 'Press Start 2P'; font-size: 2em;
            text-shadow: 2px 2px 0 #000;
        }

        .card-inner-text {
            border: 2px dashed #ccc;
            flex-grow: 1; display: flex; align-items: center; justify-content: center;
            font-family: 'VT323', monospace; font-size: 2em; font-weight: bold;
            line-height: 1.1; word-break: break-word;
        }
        
        .card-creator-tag {
            font-size: 0.8em; color: #fff;
            background: #1a1a1a; padding: 2px 5px;
            font-family: 'Press Start 2P'; margin-top: 5px;
        }

        /* --- 按钮样式 --- */
        div.stButton > button {
            width: 100%; 
            font-family: 'Press Start 2P' !important;
            font-size: 0.8em !important;
            border: 2px solid #000; 
            box-shadow: 2px 2px 0px #000;
            margin-top: -5px;
        }
        div.stButton > button:active { 
            transform: translate(1px, 1px); 
            box-shadow: 1px 1px 0px #000; 
        }

        /* 红色删除按钮 */
        button[kind="secondary"] {
            background-color: #FF4500 !important;
            color: white !important;
            border-color: #fff !important;
        }
        /* 蓝色翻面按钮 */
        button[kind="primary"] {
            background-color: #00BFFF !important;
            color: #1a1a1a !important;
            border-color: #fff !important;
        }

        </style>
        <div class="crt-overlay"></div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 3. HTML 渲染
# ==============================================================================

def draw_card_html(text, creator, color_hex, tilt_seed, is_revealed):
    border_color = color_hex
    tilt = (tilt_seed % 10) - 5
    
    if is_revealed:
        # 正面：显示 JOKER 标 + 内容 + 创建者条
        inner = f'<div style="position:absolute; top:2px; right:5px; font-family:\'Press Start 2P\'; font-size:0.6em; color:#555;">GOOD EATS!</div><div class="card-inner-text">{text}</div>'
        tag = f'<div class="card-creator-tag" style="background-color:{border_color};">{creator}</div>'
    else:
        # 背面：只显示问号
        inner = f'<div class="card-back-pattern">?</div>'
        tag = '' 
    
    return f'<div class="poker-card" style="border-bottom: 8px solid {border_color}; transform: rotate({tilt}deg);">{inner}{tag}</div>'

# ==============================================================================
# 4. 局部刷新逻辑
# ==============================================================================

@st.fragment(run_every=2)
def render_active_game_board(current_room_id, nickname, user_id, my_color):
    db = SessionLocal()
    try:
        room = db.query(Room).filter(Room.id == current_room_id).first()
        cards = db.query(CardOption).filter(CardOption.room_id == current_room_id).all()
        
        if not room:
            st.error("Room connection lost.")
            return

        # --- A. 结果展示 ---
        if room.status == "RESULT":
            st.markdown(f'<h1 class="glitch-title">WINNER!</h1>', unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#FFD700; border:6px solid #fff; padding:40px; text-align:center; color:#000; font-family:'Press Start 2P'; box-shadow:0 0 30px {my_color}; transform: rotate(-2deg);">
                <div style="font-size:1.2em;">THE CHOSEN MEAL</div>
                <div style="font-size:3em; margin-top:10px;">{room.winner_text}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            if nickname == room.host_name:
                if st.button("NEW ROUND", type="primary", use_container_width=True):
                    room.status = "WAITING"
                    room.winner_text = None
                    st.session_state.revealed_card_id = None
                    db.commit()
                    st.rerun()
            else:
                st.info("Waiting for host to restart...")

        # --- B. 抽卡动画 ---
        elif room.status == "SPINNING":
            st.markdown('<h1 class="glitch-title" style="color: #00BFFF;">SHUFFLING...</h1>', unsafe_allow_html=True)
            placeholder = st.empty()
            if nickname == room.host_name:
                animation_cards = [c.text for c in cards] if cards else ["???"]
                for _ in range(15):
                    temp_text = random.choice(animation_cards)
                    temp_color = random.choice(COLOR_PALETTE)
                    placeholder.markdown(f"""
                    <div style="display:flex; justify-content:center;">
                        <div class="poker-card" style="width:200px; height:280px; transform:rotate({random.randint(-10,10)}deg); border-color:{temp_color};">
                            <div class="card-inner-text" style="font-size:3em;">{temp_text}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    time.sleep(0.1)
                
                if cards:
                    winner = random.choice(cards)
                    room.winner_text = winner.text
                    room.status = "RESULT"
                    db.commit()
                    st.rerun()
            else:
                st.markdown("<div style='text-align:center; font-size:1.5em;'>DEALING DESTINY...</div>", unsafe_allow_html=True)

        # --- C. 等待/卡牌管理 ---
        else:
            my_card_count = db.query(CardOption).filter(
                CardOption.room_id == current_room_id,
                CardOption.user_token == user_id
            ).count()
            remaining_slots = MAX_CARDS_PER_USER - my_card_count

            col_input, col_info = st.columns([3, 1])
            with col_input:
                with st.form("add_card_form", clear_on_submit=True):
                    c1, c2 = st.columns([3, 1])
                    placeholder_txt = f"Add Option ({remaining_slots} left)" if remaining_slots > 0 else "HAND FULL"
                    new_option = c1.text_input("Card Text", placeholder=placeholder_txt, label_visibility="collapsed", disabled=(remaining_slots <= 0))
                    submitted = c2.form_submit_button("ADD CARD", type="primary", disabled=(remaining_slots <= 0))
                    
                    if submitted and new_option and remaining_slots > 0:
                        new_card = CardOption(
                            room_id=current_room_id,
                            text=new_option,
                            creator=nickname,
                            user_token=user_id,
                            tilt_seed=random.randint(0, 100)
                        )
                        db.add(new_card)
                        db.commit()
                        st.rerun()

            with col_info:
                if nickname == room.host_name:
                    if len(cards) > 0:
                        if st.button("▶ START", type="primary", use_container_width=True):
                            room.status = "SPINNING"
                            db.commit()
                            st.rerun()
                    else:
                        st.caption("Waiting for cards...")
                else:
                    st.caption(f"Host: {room.host_name}")

            st.markdown("---")

            # --- 核心：卡片渲染 ---
            if cards:
                room_users = db.query(RoomUser).filter(RoomUser.room_id == current_room_id).all()
                color_map = {u.nickname: u.color_hex for u in room_users}

                cols = st.columns(4)
                for idx, card in enumerate(cards):
                    card_color = color_map.get(card.creator, "#ccc")
                    
                    # 逻辑判定：
                    # 1. 自己的卡片 -> 始终显示正面 (True)
                    # 2. 别人的卡片 -> 看 revealed_card_id 是否匹配
                    is_mine = (card.user_token == user_id)
                    is_revealed = is_mine or (st.session_state.revealed_card_id == card.id)
                    
                    with cols[idx % 4]:
                        # 渲染 HTML
                        st.markdown(draw_card_html(card.text, card.creator, card_color, card.tilt_seed, is_revealed), unsafe_allow_html=True)
                        
                        # 渲染按钮
                        if is_mine:
                            # 自己的卡：只显示红色的“删除”按钮
                            if st.button("删除", key=f"del_{card.id}", type="secondary", use_container_width=True):
                                db.delete(card)
                                db.commit()
                                # 如果正好删的是翻开的那张（理论上不需要，因为只有别人的才需要翻），防守性重置
                                if st.session_state.revealed_card_id == card.id:
                                    st.session_state.revealed_card_id = None
                                st.rerun()
                        else:
                            # 别人的卡：显示蓝色的“翻开/盖上”按钮
                            # 如果当前已翻开，显示 "盖上"，否则显示 "翻开"
                            btn_text = "盖上" if is_revealed else "翻开"
                            if st.button(btn_text, key=f"flip_{card.id}", type="primary", use_container_width=True):
                                if is_revealed:
                                    st.session_state.revealed_card_id = None
                                else:
                                    st.session_state.revealed_card_id = card.id
                                st.rerun()
            else:
                st.markdown("<div style='text-align:center; padding:50px; color:#666;'>TABLE EMPTY</div>", unsafe_allow_html=True)

    finally:
        db.close()

# ==============================================================================
# 5. 主入口
# ==============================================================================

def main():
    inject_balatro_css()

    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())[:8]
    if 'init_random_room' not in st.session_state:
        st.session_state.init_random_room = str(random.randint(1000, 9999))
    if 'revealed_card_id' not in st.session_state:
        st.session_state.revealed_card_id = None

    # --- 阶段 1: 登录 ---
    if "nickname" not in st.session_state:
        login_placeholder = st.empty()
        with login_placeholder.container():
            query_params = st.query_params
            room_id_from_url = query_params.get("room", None)
            default_room_val = room_id_from_url if room_id_from_url else st.session_state.init_random_room

            st.markdown('<h1 class="glitch-title">BALATRO EATS</h1>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                nickname = st.text_input("ENTER NICKNAME", max_chars=10)
                room_input = st.text_input("ROOM ID", value=default_room_val)
                if st.button("INSERT COIN", use_container_width=True, type="primary"):
                    if nickname and room_input:
                        st.session_state.nickname = nickname
                        st.session_state.room_id = room_input
                        st.query_params["room"] = room_input
                        login_placeholder.empty()
                        st.rerun()

    # --- 阶段 2: 游戏大厅 ---
    else:
        db = SessionLocal()
        current_room_id = st.session_state.room_id
        nickname = st.session_state.nickname
        user_id = st.session_state.user_id

        room = db.query(Room).filter(Room.id == current_room_id).first()
        if not room:
            room = Room(id=current_room_id, host_name=nickname, status="WAITING", last_updated=str(time.time()))
            db.add(room)
            db.commit()
        
        my_color = get_user_color(db, current_room_id, user_id, nickname)
        db.close()

        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:flex-end; border-bottom: 2px solid #555; padding-bottom:10px; margin-bottom:20px;">
            <div>PLAYER: <span style="color:{my_color}; font-size:1.2em; text-shadow:2px 2px 0 #000;">{nickname}</span></div>
            <div style="font-family:'Press Start 2P'">ROOM: <span style="color:#FFD700">{current_room_id}</span></div>
        </div>
        """, unsafe_allow_html=True)

        render_active_game_board(current_room_id, nickname, user_id, my_color)

if __name__ == "__main__":
    main()