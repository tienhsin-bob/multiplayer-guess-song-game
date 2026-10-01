# 多人連線猜歌遊戲 🎵

這是一個使用 Python 開發的多人連線猜歌遊戲，結合 **TCP / UDP Socket Programming、Multithreading 與 Tkinter GUI**，為網路程式設計課程期末專題。

## 🎬 專案展示影片

[▶️ YouTube Demo](https://youtu.be/A3YwKKJ_NSU?si=IxcItGC284kgYk2X)

## 🎮 專案介紹

玩家透過 Client 連線至 Server，進行多人即時猜歌競賽。

遊戲開始後，Server 會逐步將歌詞廣播給所有玩家，玩家可以猜測 **歌曲名稱** 與 **歌手名稱**。Server 負責管理遊戲流程、玩家狀態、答案判定以及即時計分。

每場遊戲共有 **5 個回合**，最後依照玩家得分顯示比賽結果。

## ✨ 主要功能

- 多人 Client-Server 連線
- 玩家大廳與準備機制
- 隨機玩家頭像
- 遊戲開始前倒數
- 五回合猜歌競賽
- 即時歌詞廣播
- 歌名與歌手答案判定
- 即時計分與排行榜
- 遊戲結束勝負判定
- 玩家斷線處理
- 提供 PyInstaller 打包後的執行檔

## 🌐 網路架構

本專案同時使用 **TCP** 與 **UDP** 進行網路通訊。

### TCP

主要負責需要可靠傳輸的資訊，例如：

- Client 與 Server 建立連線
- 玩家狀態同步
- 遊戲流程控制
- 玩家作答與計分資訊

### UDP

主要負責：

- 將遊戲中的歌詞即時廣播給所有玩家

Server 另外使用 **Threading** 處理多個 Client，使多位玩家能夠同時連線並進行遊戲。

## 🛠 使用技術

- Python
- Socket Programming
- TCP / UDP
- Threading
- Tkinter
- Pillow
- JSON
- PyInstaller

## 📁 專案結構

```text
multiplayer-guess-song-game/
├── FinalClient.py
├── FinalServer.py
├── questions.json
├── avatars/
├── dist/
└── 使用說明/
```

### 主要檔案說明

- `FinalClient.py`：Client 程式與 Tkinter 使用者介面
- `FinalServer.py`：Server 程式與多人遊戲流程控制
- `questions.json`：遊戲題目與歌曲資料
- `avatars/`：玩家頭像圖片
- `dist/`：PyInstaller 打包後的執行檔
- `使用說明/`：原始程式使用說明

## ▶️ 執行方式

詳細操作方式請參考：

[`使用說明`](./使用說明)

專案中的 `dist/` 資料夾亦包含已使用 PyInstaller 打包完成的 Client 與 Server 執行檔。

## 📚 學習收穫

透過本專題，我實際練習並整合了：

- Client-Server 網路程式架構
- TCP 與 UDP 的應用與差異
- 多執行緒處理多人連線
- 多玩家遊戲狀態同步
- 網路通訊與 Tkinter GUI 的整合
- JSON 題庫資料管理
- Python 程式打包與部署
