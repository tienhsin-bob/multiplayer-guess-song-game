
import socket
import threading
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import json
import os
import random
import traceback

HOST = "127.0.0.1"
PORT = 12346
UDP_PORT = 54321

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AVATAR_DIR = os.path.join(BASE_DIR, "avatars")

RULES_TEXT = (
    "1. 所有玩家都按下準備鍵，遊戲才會開始。\n"
    "2. 系統將在畫面上方每 4 秒播放一句歌詞，共 5 回合。\n"
    "3. 玩家可依據格式提問 (例如：歌名幾個字？)。\n"
    "4. 每回合需分別猜中「歌名」與「歌手」，答對一個得 1 分。\n"
    "5. 若先答錯再答對，則不加分。\n"
    "6. 若均有人猜出，則提早進入下一題，否則直到歌曲結束才結束該回合。\n"
    "7. 若有玩家在遊戲中退出，則遊戲中止，其餘玩家可返回遊戲大廳。"
)

class GuessSongClient:
    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("猜歌遊戲")
        self.master.configure(bg="#f4f4f4")
        self.placeholder = "性別、國籍、歌手幾個字、歌名幾個字、是團體嗎"

        # TCP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((HOST, PORT))
        except Exception:
            traceback.print_exc()
            self.master.destroy()
            return

        # UDP 廣播接收
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.bind(("", UDP_PORT))
        threading.Thread(target=self.listen_udp, daemon=True).start()

        self.in_game = False
        self.name = ""
        self.lyric_queue = []
        self.avatar_img = None

        if os.path.isdir(AVATAR_DIR):
            pngs = [f for f in os.listdir(AVATAR_DIR) if f.lower().endswith('.png')]
            if pngs:
                path = os.path.join(AVATAR_DIR, random.choice(pngs))
                img = Image.open(path).resize((64, 64), Image.Resampling.LANCZOS)
                self.avatar_img = ImageTk.PhotoImage(img)

        threading.Thread(target=self.receive_loop, daemon=True).start()
        self.build_name_screen()

    def listen_udp(self):
        while True:
            try:
                data, _ = self.udp_socket.recvfrom(1024)
                msg = data.decode()
                self.master.after(0, lambda: self.append_output(f"📣 廣播：{msg}"))
            except:
                continue

    def clear(self):
        for w in self.master.winfo_children():
            w.destroy()

    def build_name_screen(self):
        self.master.geometry("300x200")
        self.master.minsize(300, 200)
        self.clear()
        ttk.Label(self.master, text="請輸入玩家名稱：").pack(pady=10)
        self.e_name = ttk.Entry(self.master, font=("微軟正黑體", 12))
        self.e_name.pack(pady=5)
        ttk.Button(self.master, text="加入遊戲", command=self.login).pack(pady=10)

    def login(self):
        name = self.e_name.get().strip()
        if not name:
            return
        self.name = name
        self.sock.sendall((name + "\n").encode())
        self.build_lobby()

    def build_lobby(self):
        self.master.geometry("800x500")
        self.master.minsize(700, 450)
        self.clear()
        ttk.Label(self.master, text="🎵 猜歌小遊戲 🎵", font=("微軟正黑體", 16, "bold")).pack(pady=10)
        if self.avatar_img:
            tk.Label(self.master, image=self.avatar_img, bg="#f4f4f4").pack(pady=5)
        ttk.Label(self.master, text=f"歡迎 {self.name}！", font=("微軟正黑體", 12)).pack(pady=5)
        self.online_label = ttk.Label(self.master, text="目前在線玩家：等待回傳…", font=("微軟正黑體", 12))
        self.online_label.pack(pady=5)
        self.ready_btn = ttk.Button(self.master, text="我已準備", command=self.send_ready)
        self.ready_btn.pack(pady=5)
        ttk.Button(self.master, text="離開遊戲", command=self.exit_game).pack(pady=5)
        ttk.Label(self.master, text="— 遊戲規則 —", font=("微軟正黑體", 12)).pack(pady=(10, 0))
        tk.Message(self.master, text=RULES_TEXT, width=500, font=("微軟正黑體", 11), justify="left").pack(pady=5)
        self.send_json({"type": "get_online"})
        self.master.after(2000, self.request_online)

    def request_online(self):
        if not self.in_game:
            self.send_json({"type": "get_online"})
        self.master.after(2000, self.request_online)

    def send_ready(self):
        self.send_json({"type": "ready"})
        self.ready_btn.config(text="✔ 已準備", state="disabled")

    def build_game_ui(self):
        self.in_game = True
        self.clear()
        ttk.Separator(self.master, orient="horizontal").pack(fill=tk.X, pady=5)
        ttk.Label(self.master, text="🎯 記分板", font=("微軟正黑體", 14, "bold")).pack(pady=5)
        self.score_table = tk.Text(
            self.master, height=2, state="disabled", bd=0, highlightthickness=0,
            font=("微軟正黑體", 12), spacing1=4, spacing3=4
        )
        self.score_table.tag_configure("center", justify="center")
        self.score_table.pack(fill=tk.X, padx=10)
        self.send_json({"type": "get_scoreboard"})
        self.master.after(2000, self.request_scoreboard)

        lf = ttk.LabelFrame(self.master, text="歌詞輸出", padding=10)
        lf.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.lyrics_display = tk.Text(
            lf, height=4, state="disabled", wrap="word",
            bd=0, highlightthickness=0, font=("微軟正黑體", 14), spacing1=6, spacing3=6
        )
        self.lyrics_display.tag_configure("center", justify="center")
        self.lyrics_display.pack(fill=tk.BOTH, expand=True)

        ttk.Separator(self.master, orient="horizontal").pack(fill=tk.X, pady=5)
        frm = ttk.Frame(self.master)
        frm.pack(fill=tk.X, padx=10, pady=5)
        self.guess_entry = ttk.Entry(frm, width=25, font=("微軟正黑體", 12))
        self.guess_entry.grid(row=0, column=0, padx=5)
        self.cat = tk.StringVar(value="title")
        ttk.Radiobutton(frm, text="猜歌名", variable=self.cat, value="title").grid(row=0, column=1)
        ttk.Radiobutton(frm, text="猜歌手", variable=self.cat, value="singer").grid(row=0, column=2)
        ttk.Button(frm, text="送出答案", command=self.send_guess).grid(row=0, column=3, padx=5)

        ttk.Label(frm, text="提問：", font=("微軟正黑體", 12)).grid(row=1, column=0, pady=5, sticky="w")
        self.q_entry = ttk.Entry(frm, width=40, font=("微軟正黑體", 12))
        self.q_entry.grid(row=1, column=1, columnspan=2, padx=5)
        self.q_entry.insert(0, self.placeholder)
        self.q_entry.config(foreground='grey')
        self.q_entry.bind("<FocusIn>", lambda e: (
            self.q_entry.get()==self.placeholder and self.q_entry.delete(0, tk.END),
            self.q_entry.config(foreground='black')
        ))
        self.q_entry.bind("<FocusOut>", lambda e: (
            not self.q_entry.get() and self.q_entry.insert(0, self.placeholder),
            self.q_entry.config(foreground='grey')
        ))
        ttk.Button(frm, text="送出提問", command=self.send_question).grid(row=1, column=3)

        self.output_text = tk.Text(self.master, height=6, state="disabled",
                                   font=("微軟正黑體", 12), spacing1=4, spacing3=4)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def request_scoreboard(self):
        if self.in_game:
            self.send_json({"type": "get_scoreboard"})
        self.master.after(2000, self.request_scoreboard)

    def send_guess(self):
        ans = self.guess_entry.get().strip()
        if ans:
            self.send_json({"type": "guess", "player": self.name, "answer": ans, "category": self.cat.get()})
        self.guess_entry.delete(0, tk.END)

    def send_question(self):
        q = self.q_entry.get().strip()
        if q and q != self.placeholder:
            self.send_json({"type": "question", "question": q})
        self.q_entry.delete(0, tk.END)
        self.q_entry.insert(0, self.placeholder)
        self.q_entry.config(foreground='grey')

    def send_json(self, obj: dict):
        try:
            self.sock.sendall((json.dumps(obj) + "\n").encode())
        except:
            traceback.print_exc()

    def receive_loop(self):
        buf = ""
        while True:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                buf += data.decode()
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    if line.strip():
                        self.master.after(0, self.handle_message, json.loads(line))
            except Exception:
                traceback.print_exc()
                break

    def handle_message(self, msg: dict):
        t = msg.get("type")
        if t == "online_list":
            names = ", ".join(p["name"] for p in msg.get("players", []))
            if hasattr(self, "online_label"):
                self.online_label.config(text="目前在線玩家：" + names)
        elif t == "start_game_broadcast":
            self.build_game_ui()
        elif t == "new_question":
            rnd = msg.get("round", 1)
            if not self.in_game:
                self.build_game_ui()
            self.clear_question()
            self.lyric_queue.clear()
            self.lyrics_display.config(state="normal")
            self.lyrics_display.insert(tk.END, f"--- 第{rnd} 題 ---\n", "center")
            self.lyrics_display.config(state="disabled")
            self.master.after(3000, self.play_next_line)
        elif t == "lyrics_line":
            line = msg.get("line", "")
            if line:
                self.lyric_queue.append(line)
        elif t == "player_ready":
            self.append_output(f"✔ {msg.get('player')} 已準備")
        elif t == "result":
            tip = "✅" if msg.get("scored") else "☑️"
            extra = "" if msg.get("scored") else "（已猜錯過，0 分）"
            self.append_output(f"{tip} {msg.get('winner')} 猜對 {msg.get('category')}：{msg.get('answer')} {extra}")
        elif t == "answer":
            reply = msg.get("reply", "")
            if reply == "3 秒後開始遊戲...":
                self.show_countdown_screen(reply)
            else:
                self.append_output(f"💡 {reply}")

        elif t == "scoreboard":
            scores = msg.get("scores", {})
            self.score_table.config(state="normal")
            self.score_table.delete("1.0", tk.END)
            line = "　　".join(f"{n}：{s} 分" for n, s in scores.items())
            self.score_table.insert(tk.END, line, ("center",))
            self.score_table.config(state="disabled")
            self.score_table.see(tk.END)
            
        elif t == "force_reset":
            self.in_game = False
            self.append_output("⚠️ 有玩家離線，遊戲已被強制中止。")
            self.show_reset_message()

        elif t == "game_over":
            self.show_game_over(msg.get("winner"), msg.get("scores", {}))
            
    def show_reset_message(self):
        self.clear()
        self.master.configure(bg="white")

        ttk.Label(
            self.master,
            text="⚠️ 遊戲中有玩家離線，遊戲已中止",
            font=("微軟正黑體", 16, "bold"),
            foreground="red"
        ).pack(pady=30)

        ttk.Button(
            self.master,
            text="回到大廳",
            command=self.build_lobby
        ).pack(pady=20)

    def play_next_line(self):
        if not self.lyric_queue:
            return
        line = self.lyric_queue.pop(0)
        self.append_lyrics(line)
        self.master.after(4000, self.play_next_line)

    def clear_question(self):
        self.lyrics_display.config(state="normal")
        self.lyrics_display.delete("1.0", tk.END)
        self.lyrics_display.config(state="disabled")
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state="disabled")

    def append_lyrics(self, line: str):
        self.lyrics_display.config(state="normal")
        self.lyrics_display.insert(tk.END, line + "\n", "center")
        self.lyrics_display.see(tk.END)
        self.lyrics_display.config(state="disabled")

    def append_output(self, text: str):
        self.output_text.config(state="normal")
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
        self.output_text.config(state="disabled")

    def show_countdown_screen(self, message):
        self.clear()
        self.master.configure(bg="white")

        self.countdown_label = ttk.Label(
            self.master,
            text=message,
            font=("微軟正黑體", 24, "bold"),
            foreground="#444"
        )
        self.countdown_label.place(relx=0.5, rely=0.5, anchor="center")

        self.countdown_value = 3
        self.update_countdown()

    def update_countdown(self):
        if self.countdown_value <= 0:
            return  # 等 server 發出 start_game_broadcast 再轉畫面
        text = f"{self.countdown_value} 秒後開始遊戲..."
        self.countdown_label.config(text=text)
        self.countdown_value -= 1
        self.master.after(1000, self.update_countdown)
    
    def show_game_over(self, winner, scores: dict):
        self.in_game = False
        self.clear()
        ttk.Label(
            self.master,
            text=("平手" if winner == "平手" else f"勝利者：{winner}"),
            font=("微軟正黑體", 16, "bold")
        ).pack(pady=20)
        for n, s in scores.items():
            ttk.Label(self.master, text=f"{n}：{s} 分").pack()
        ttk.Button(self.master, text="回到大廳", command=self.build_lobby).pack(pady=20)

    def exit_game(self):
        try:
            self.sock.sendall((json.dumps({"type": "exit_game"}) + "\n").encode())
        except Exception:
            pass
        self.sock.close()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = GuessSongClient(root)
    root.mainloop()
 
