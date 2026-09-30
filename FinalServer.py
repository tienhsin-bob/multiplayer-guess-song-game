import socket
import threading
import json
import time
import random
import re

HOST, PORT = "0.0.0.0", 12346
UDP_PORT = 54321

clients = []
player_names = {}
player_avatars = {}
scores = {}
ready_players = set()

current_question = {}
guessed_correctly = {"title": False, "singer": False}
wrong_guesses = {}
current_round = 0
game_started = False
starter_conn = None
question_id_counter = 0

TOTAL_ROUNDS = 5
LYRIC_INTERVAL = 4
start_lock = threading.Lock()

with open("questions.json", "r", encoding="utf-8") as f:
    question_bank = json.load(f)

def broadcast(msg: dict):
    raw = (json.dumps(msg) + "\n").encode()
    dead = []
    for c in clients:
        try:
            c.sendall(raw)
        except:
            dead.append(c)
    for d in dead:
        remove_client(d)

def udp_broadcast(text: str):
    try:
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_sock.sendto(text.encode(), ("<broadcast>", UDP_PORT))
        udp_sock.close()
    except:
        pass

def send_to(conn, msg: dict):
    try:
        conn.sendall((json.dumps(msg) + "\n").encode())
    except:
        remove_client(conn)

def broadcast_online():
    player_list = [
        {"name": player_names[c], "avatar": player_avatars.get(c, 0)}
        for c in clients if c in player_names
    ]
    broadcast({"type": "online_list", "players": player_list})

def remove_client(conn):
    global game_started
    name = player_names.pop(conn, None)
    player_avatars.pop(conn, None)
    if conn in clients:
        clients.remove(conn)
    if name:
        scores.pop(name, None)
        wrong_guesses.pop(name, None)
        ready_players.discard(conn)
        print(f"[移除] {name} 離開，更新在線人數")

    if game_started:
        print("[警告] 有玩家離線，遊戲強制中止")
        broadcast({"type": "answer", "reply": "⚠️ 有玩家離線，遊戲已被中止。"})
        broadcast({"type": "force_reset"})
        game_reset()

    broadcast_online()
    try:
        conn.close()
    except:
        pass

def handle_client(conn, addr):
    global game_started, starter_conn
    try:
        name = conn.recv(1024).decode().strip()
        if not name:
            return
        clients.append(conn)
        player_names[conn] = name
        print(f"[登入] {addr} -> {name}")
    except:
        remove_client(conn)
        return

    while True:
        try:
            data = conn.recv(4096).decode()
            if not data:
                break
            for line in data.strip().split("\n"):
                if not line.strip():
                    continue
                msg = json.loads(line)
                t = msg.get("type")

                if "avatar" in msg:
                    player_avatars[conn] = msg["avatar"]

                if t == "get_online":
                    send_to(conn, {
                        "type": "online_list",
                        "players": [
                            {"name": player_names.get(c), "avatar": player_avatars.get(c, 0)}
                            for c in clients if c in player_names
                        ]
                    })

                elif t == "ready":
                    ready_players.add(conn)
                    broadcast({"type": "player_ready", "player": player_names[conn]})
                    active_players = set(player_names.keys())
                    with start_lock:
                        if ready_players == active_players and not game_started:
                            starter_conn = conn
                            broadcast({"type": "answer", "reply": "3 秒後開始遊戲..."})
                            threading.Timer(3, start_game).start()

                elif t == "guess" and game_started:
                    name, ans, cat = msg["player"], msg["answer"].strip(), msg["category"]
                    if guessed_correctly[cat]:
                        continue
                    correct = (
                        ans == current_question["答案"] if cat == "title"
                        else ans == current_question["歌手"]
                    )
                    if correct:
                        scored = not wrong_guesses[name][cat]
                        if scored:
                            scores[name] += 1
                        guessed_correctly[cat] = True
                        broadcast({
                            "type": "result", "winner": name,
                            "category": cat, "answer": ans, "scored": scored
                        })
                        broadcast({"type": "scoreboard", "scores": scores})
                        if all(guessed_correctly.values()):
                            threading.Timer(3, next_question).start()
                    else:
                        wrong_guesses[name][cat] = True

                elif t == "question":
                    q = msg["question"].lower()
                    a = current_question
                    reply = "提問格式有誤，請再試一次。"

                    if "性別" in q:
                        if a.get("類型") == "團體":
                            reply = "這是一個團體，成員可能包含不同性別喔。"
                        else:
                            reply = f"歌手是 {a['性別']} 性。"
                    elif "國籍" in q:
                        reply = f"歌手是 {a['國籍']} 人。"
                    elif "幾個字" in q and "歌名" in q:
                        reply = f"歌名有 {len(a['答案'])} 個字。"
                    elif "幾個字" in q and "歌手" in q:
                        reply = f"歌手名字有 {len(a['歌手'])} 個字。"
                    elif "團體" in q:
                        reply = "是的，這是一個團體。" if a.get("類型") == "團體" else "不是，這位歌手是個人歌手。"
                    elif a["歌手"] in q:
                        reply = "是的。"

                    broadcast({
                        "type": "answer",
                        "reply": f"{player_names[conn]} 提問：{q}\n👉 {reply}"
                    })

                elif t == "get_scoreboard":
                    send_to(conn, {"type": "scoreboard", "scores": scores})

                elif t == "exit_game":
                    break
        except:
            break
    remove_client(conn)
    print(f"[離線] {addr}")

def game_reset():
    global game_started, ready_players, current_round
    global current_question, guessed_correctly, wrong_guesses
    game_started = False
    ready_players.clear()
    current_round = 0
    current_question = {}
    guessed_correctly = {"title": False, "singer": False}
    wrong_guesses = {name: {"title": False, "singer": False} for name in player_names.values()}
    broadcast_online()

def start_game():
    global game_started, current_round, scores, wrong_guesses
    game_started = True
    current_round = 0
    scores = {name: 0 for name in player_names.values()}
    wrong_guesses = {name: {"title": False, "singer": False} for name in player_names.values()}
    broadcast({"type": "start_game_broadcast"})
    udp_broadcast("遊戲開始！準備好猜歌囉！")
    threading.Timer(1, next_question).start()

def next_question():
    global current_question, guessed_correctly, wrong_guesses, current_round, question_id_counter
    current_round += 1
    if current_round > TOTAL_ROUNDS:
        top = max(scores.values()) if scores else 0
        winners = [k for k, v in scores.items() if v == top]
        result = winners[0] if len(winners) == 1 else "平手"
        broadcast({"type": "game_over", "scores": scores, "winner": result})
        udp_broadcast(f"遊戲結束！{result} 獲勝！")
        game_reset()
        return

    current_question = random.choice(question_bank)
    question_id_counter += 1
    current_question["__id__"] = question_id_counter

    guessed_correctly = {"title": False, "singer": False}
    for k in scores:
        wrong_guesses[k] = {"title": False, "singer": False}

    broadcast({"type": "new_question", "round": current_round})
    udp_broadcast(f"第 {current_round} 題開始囉，快來搶答！")
    threading.Thread(target=play_lyrics, args=(current_question["__id__"],), daemon=True).start()

def play_lyrics(qid):
    lines = re.split(r"[，,\n]", current_question.get("歌詞", ""))
    lines = [l.strip() for l in lines if l.strip()]
    for line in lines:
        if not game_started or current_question.get("__id__") != qid:
            break
        if all(guessed_correctly.values()):
            break
        broadcast({"type": "lyrics_line", "line": line})
        time.sleep(LYRIC_INTERVAL)
    else:
        time.sleep(3)
        if game_started and current_question.get("__id__") == qid:
            title = current_question.get("答案", "未知歌名")
            singer = current_question.get("歌手", "未知歌手")
            broadcast({
                "type": "answer",
                "reply": f"🛎️ 本題結束，正確答案是：\n🎵 歌名：{title}\n👤 歌手：{singer}"
            })
            threading.Timer(2, next_question).start()

# 主程式入口
print("[伺服器啟動] 等待玩家連線中...")
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind((HOST, PORT))
srv.listen()

while True:
    c, a = srv.accept()
    threading.Thread(target=handle_client, args=(c, a), daemon=True).start()
