"""
Discord Gateway + HTTP Client:
  - Gateway: đọc Spotify activity (artist, title, timestamp chính xác)
  - HTTP:    set custom status (đáng tin cậy hơn Gateway OP 3)

Spotify activity có trong presence có dạng:
  {
    "name": "Spotify",
    "type": 2,  # LISTENING
    "details": "Song Title",
    "state": "Artist Name",
    "timestamps": {"start": 1234567890000, "end": 1234570000000},
    "assets": {"large_text": "Album Name", ...}
  }
"""

import json
import threading
import time
from dataclasses import dataclass
from typing import Optional

import requests
import websocket

import config

GATEWAY_URL = "wss://gateway.discord.gg/?v=9&encoding=json"
HTTP_BASE = "https://discord.com/api/v9"


@dataclass
class SpotifyTrack:
    """Track info từ Discord Spotify presence."""
    title: str
    artist: str
    album: str = ""
    url: str = ""
    start_ms: int = 0      # Unix ms — thời điểm bắt đầu phát
    end_ms: int = 0        # Unix ms — thời điểm kết thúc
    is_playing: bool = True

    @property
    def elapsed_sec(self) -> float:
        """Số giây đã trôi qua của bài hát (chính xác từ timestamp Spotify)."""
        if not self.start_ms:
            return 0.0
        return max(0.0, (time.time() * 1000 - self.start_ms) / 1000)

    @property
    def track_id(self) -> str:
        return f"{self.title}|{self.artist}"


class DiscordClient:
    """Quản lý cả Gateway (đọc Spotify) + HTTP (set status)."""

    def __init__(self):
        # Gateway
        self.ws: Optional[websocket.WebSocketApp] = None
        self._running = False
        self._ready = threading.Event()
        self._seq: Optional[int] = None
        self._heartbeat_interval: float = 30
        self._heartbeat_thread: Optional[threading.Thread] = None

        # Spotify track hiện tại
        self._current_track: Optional[SpotifyTrack] = None
        self._track_lock = threading.Lock()

        # HTTP headers
        self._http_headers = {
            "Authorization": config.DISCORD_USER_TOKEN,
            "Content-Type": "application/json",
        }
        self._last_status: Optional[str] = None

    # ==================== Gateway ====================

    def connect(self) -> bool:
        """Kết nối Gateway và xác thực."""
        self._running = True
        self._ready.clear()

        # Verify token qua HTTP trước
        if not self._verify_http():
            return False

        self.ws = websocket.WebSocketApp(
            GATEWAY_URL,
            on_open=self._on_open,
            on_message=self._on_message,
            on_close=self._on_close,
            on_error=self._on_error,
        )

        t = threading.Thread(target=self.ws.run_forever, daemon=True)
        t.start()

        if not self._ready.wait(timeout=30):
            print("[Gateway] Timeout!")
            return False

        print("[Gateway] ✅ Kết nối thành công!")
        return True

    def _verify_http(self) -> bool:
        try:
            resp = requests.get(f"{HTTP_BASE}/users/@me", headers=self._http_headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                print(f"[Discord] ✅ {data['username']}")
                return True
            print(f"[Discord] ❌ HTTP {resp.status_code}")
            return False
        except Exception as e:
            print(f"[Discord] ❌ {e}")
            return False

    def _send_gateway(self, op: int, data: dict):
        if self.ws:
            self.ws.send(json.dumps({"op": op, "d": data}))

    def _on_open(self, ws):
        print("[Gateway] WebSocket opened")
        self._send_gateway(2, {
            "token": config.DISCORD_USER_TOKEN,
            "capabilities": 8189,
            "properties": {
                "os": "Windows",
                "browser": "Chrome",
                "device": "",
                "system_locale": "en-US",
                "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "browser_version": "131.0.0.0",
                "os_version": "10",
                "referrer": "",
                "referring_domain": "",
                "referrer_current": "",
                "referring_domain_current": "",
                "release_channel": "stable",
                "client_build_number": 9999,
                "client_event_source": None,
            },
            "presence": {
                "since": None,
                "activities": [],
                "status": "online",
                "afk": False,
            },
        })

    def _on_message(self, ws, message: str):
        data = json.loads(message)
        op = data.get("op")
        seq = data.get("s")
        if seq is not None:
            self._seq = seq

        if op == 10:  # Hello
            self._heartbeat_interval = data["d"]["heartbeat_interval"] / 1000
            print(f"[Gateway] Hello (heartbeat: {self._heartbeat_interval:.0f}s)")
            self._start_heartbeat()

        elif op == 0:  # Dispatch
            t = data.get("t")
            d = data.get("d", {})

            if t == "READY":
                user = d.get("user", {})
                print(f"[Gateway] READY: {user.get('username', '?')}")

                # Spotify activity có thể ở d["presence"] hoặc user["presence"]
                pres = d.get("presence") or user.get("presence") or {}
                self._parse_spotify_from_presence(pres)

                self._ready.set()

            elif t == "SESSIONS_REPLACE":
                # Gom tất cả activities từ mọi session, tìm Spotify
                all_activities = []
                for session in d:
                    all_activities.extend(session.get("activities", []))
                self._parse_spotify_from_activities(all_activities)

            elif t == "PRESENCE_UPDATE":
                self._parse_spotify_from_presence(d)

        elif op == 7:
            print("[Gateway] Reconnect requested")
        elif op == 9:
            print("[Gateway] Invalid session")

    def _parse_spotify_from_presence(self, presence: dict):
        """Tìm Spotify activity trong presence và extract track info."""
        self._parse_spotify_from_activities(presence.get("activities", []))

    def _parse_spotify_from_activities(self, activities: list):
        """Extract Spotify track từ list activities. Chỉ SET, không CLEAR."""
        for act in activities:
            if act.get("name") == "Spotify":
                timestamps = act.get("timestamps", {})
                track = SpotifyTrack(
                    title=act.get("details", ""),
                    artist=act.get("state", ""),
                    album=act.get("assets", {}).get("large_text", "") if act.get("assets") else "",
                    url=f"https://open.spotify.com/track/{act.get('sync_id', '')}" if act.get("sync_id") else "",
                    start_ms=int(timestamps.get("start", 0)),
                    end_ms=int(timestamps.get("end", 0)),
                    is_playing=True,
                )
                if not self._current_track or self._current_track.start_ms != track.start_ms:
                    print(f"[Gateway] 🎵 Spotify: {track.artist} — {track.title}")
                with self._track_lock:
                    self._current_track = track
                return

        # Không clear ở đây — main loop tự quyết định khi nào track đã kết thúc
        # (SESSIONS_REPLACE fire quá nhiều, mỗi event có thể thiếu Spotify tạm thời)

    def _on_close(self, ws, code, msg):
        print(f"[Gateway] Closed (code={code})")
        self._ready.clear()
        if self._running:
            time.sleep(5)
            self.connect()

    def _on_error(self, ws, error):
        print(f"[Gateway] Error: {error}")

    def _start_heartbeat(self):
        def loop():
            while self._running:
                if self._seq is not None:
                    self._send_gateway(1, self._seq)
                time.sleep(self._heartbeat_interval * 0.5)

        self._heartbeat_thread = threading.Thread(target=loop, daemon=True)
        self._heartbeat_thread.start()

    def disconnect(self):
        self._running = False
        if self.ws:
            self.ws.close()

    # ==================== Public API ====================

    def get_current_track(self) -> Optional[SpotifyTrack]:
        """Trả về track Spotify hiện tại (từ Discord presence)."""
        with self._track_lock:
            return self._current_track

    def wait_ready(self, timeout: float = 15) -> bool:
        return self._ready.wait(timeout=timeout)

    # ==================== HTTP Status ====================

    def set_custom_status(self, text: str):
        """Cập nhật custom status qua HTTP."""
        if text == self._last_status:
            return

        self._last_status = text
        try:
            resp = requests.patch(
                f"{HTTP_BASE}/users/@me/settings",
                headers=self._http_headers,
                json={"custom_status": {"text": text}},
                timeout=10,
            )
            if resp.status_code == 200:
                print(f"[Discord] ✅ Status: {text}")
            elif resp.status_code == 429:
                retry = resp.json().get("retry_after", 5)
                print(f"[Discord] ⚠️ Rate limited ({retry}s)")
            else:
                print(f"[Discord] ❌ {resp.status_code}: {resp.text[:100]}")
        except requests.RequestException as e:
            print(f"[Discord] ❌ Network: {e}")
