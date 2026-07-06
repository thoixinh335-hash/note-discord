"""
NOTE DISCORD — Tự động đổi custom status Discord theo LỜI BÀI HÁT đang phát.

Cách dùng:
  1. Copy .env.example -> .env, điền DISCORD_USER_TOKEN
  2. Link Spotify với Discord (bắt buộc — để Discord nhận Spotify presence)
  3. Chạy:      python main.py

Flow:
  - Discord Gateway cung cấp Spotify activity (artist, title, timestamp chính xác)
  - Fetch synced lyrics từ lrclib.net
  - Sync từng dòng lyrics theo timestamp Spotify → update Discord status qua HTTP
"""

import time
import signal
import sys

from lyrics_client import LyricsClient, SyncedLyrics
from discord_updater import DiscordClient
import config


def main():
    print("=" * 50)
    print("  🎵 NOTE DISCORD — Lyrics -> Discord Status")
    print("=" * 50)
    print()

    # --- Discord (Gateway + HTTP) ---
    print("[Discord] Đang kết nối...")
    discord = DiscordClient()

    if not discord.connect():
        print("❌ Không thể kết nối Discord!")
        print("   Kiểm tra DISCORD_USER_TOKEN trong .env")
        print("   Đảm bảo đã link Spotify với Discord!")
        sys.exit(1)

    # --- Lyrics ---
    lyrics_client = LyricsClient()

    # --- State ---
    current_start_ms: int = 0  # Dùng start_ms để detect bài mới (chính xác nhất)
    current_lyrics: SyncedLyrics = SyncedLyrics()
    last_lyric_line: str = ""
    no_track_count = 0

    # --- Graceful shutdown ---
    def shutdown(sig, frame):
        print("\n👋 Đang thoát...")
        discord.set_custom_status("")
        time.sleep(0.5)
        discord.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"\n📍 Bắt đầu theo dõi...")
    print("   Nhấn Ctrl+C để thoát.\n")

    while True:
        track = discord.get_current_track()

        if track and track.is_playing and track.start_ms:
            no_track_count = 0

            # Bài mới? (detect bằng start_ms — timestamp Spotify thay đổi khi bài mới)
            if track.start_ms != current_start_ms:
                print(f"\n🎵 Bài mới: {track.artist} — {track.title}")
                print(f"   Timestamp: {track.start_ms} (offset: {track.elapsed_sec:.1f}s)")
                print(f"   Đang tìm lyrics...")

                current_lyrics = lyrics_client.fetch(track.artist, track.title)

                if current_lyrics.is_empty:
                    print(f"   ⚠️ Không tìm thấy synced lyrics, hiển thị tên bài")
                    status = config.STATUS_FORMAT.format(
                        artist=track.artist, title=track.title,
                        album=track.album, url=track.url,
                    )
                    discord.set_custom_status(status)
                    last_lyric_line = status
                else:
                    print(f"   ✅ {len(current_lyrics.lines)} dòng lyrics ({current_lyrics.duration_sec:.0f}s)")

                current_start_ms = track.start_ms
                last_lyric_line = ""

            # --- Hiển thị dòng lyrics hiện tại (dùng timestamp CHÍNH XÁC từ Spotify) ---
            if not current_lyrics.is_empty:
                elapsed = track.elapsed_sec  # Chính xác từ Discord/Spotify timestamps!

                line = current_lyrics.get_current_line(elapsed)

                if line and line != last_lyric_line:
                    status_text = f"🎵 {line}"
                    if len(status_text) > 128:
                        status_text = status_text[:125] + "..."
                    discord.set_custom_status(status_text)
                    print(f"🎤 [{elapsed:.0f}s] {line}")
                    last_lyric_line = line

        else:
            no_track_count += 1
            if no_track_count >= 3 and current_start_ms:
                print("⏸️  Không có nhạc, xóa status")
                discord.set_custom_status("")
                current_start_ms = 0
                current_lyrics = SyncedLyrics()
                last_lyric_line = ""

        time.sleep(config.POLL_INTERVAL)


if __name__ == "__main__":
    main()
