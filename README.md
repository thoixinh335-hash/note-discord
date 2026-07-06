# 🎵 Note Discord

Tự động thay đổi **Discord Custom Status** theo bài hát đang phát trên **Spotify**.

> 💡 **Không cần Spotify API key** — đọc trực tiếp window title của Spotify desktop app.
>
> ⚠️ **Lưu ý:** Dùng Discord user token (self-bot), vi phạm Discord ToS. Dùng cá nhân, rủi ro tự chịu.

---

## 🚀 Cài đặt

```bash
# 1. Cài dependencies
pip install -r requirements.txt

# 2. Tạo file .env
copy .env.example .env
```

## ⚙️ Cấu hình

Chỉ cần **1 thứ** — Discord user token:

```env
DISCORD_USER_TOKEN=MTIzNDU2Nzg5...  # Token Discord của bạn
```

### Lấy Discord User Token:
1. Mở Discord trên **browser** (discord.com/app)
2. **F12** → Tab **Network**
3. Bấm vào 1 request → Tìm header `Authorization`
4. Copy giá trị

---

## ▶️ Chạy

```bash
# Local
python main.py

# Hoặc VPS với PM2 (giữ process sống mãi)
npm i -g pm2
pm2 start ecosystem.config.js
pm2 save && pm2 startup   # auto-restart khi reboot
```

Lệnh PM2 thường dùng:
```bash
pm2 logs note-discord   # xem log
pm2 restart note-discord
pm2 stop note-discord
```

Kết quả: Discord custom status hiển thị **dòng lyrics đang hát** với emoji theo mood.

---

## 🛠️ Cách hoạt động

```
Spotify ──► Discord (Rich Presence)
                  │
                  │ SESSIONS_REPLACE (timestamps chính xác)
                  ▼
           discord_updater.py
           (Gateway WebSocket)         lrclib.net
                  │                        │
                  │ SpotifyTrack           │ SyncedLyrics
                  │ (artist, title,        │ (LRC format)
                  │  start_ms, end_ms)     │
                  ▼                        ▼
              main.py ─── fetch lyrics ────┘
                  │
                  │ current lyric line (synced!)
                  ▼
           Discord HTTP API
           PATCH /users/@me/settings
           "🎵 Em là ai từ đâu bước đến..."
```

- **Discord Gateway**: Nhận Spotify activity với timestamp chính xác (Unix ms)
- **lrclib.net**: API miễn phí, cung cấp LRC synced lyrics
- **Discord HTTP API**: Cập nhật custom status (ổn định hơn Gateway Presence Update)

- **spotify_client.py**: Dùng `pygetwindow` tìm cửa sổ Spotify, đọc title bar
- **discord_updater.py**: WebSocket Gateway, gửi presence update đổi custom status
- **main.py**: Poll loop 5s/lần, detect bài mới → update status

---

## 📁 Files

```
note_discord/
├── main.py              # Entry point
├── spotify_client.py    # Đọc window title Spotify (KO CẦN API)
├── discord_updater.py   # Discord Gateway WebSocket
├── config.py            # Load .env
├── .env                 # Token Discord
├── requirements.txt     # pygetwindow, websocket-client, ...
└── README.md
```
