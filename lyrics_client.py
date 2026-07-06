"""
Lyrics Client — lấy lời bài hát có timestamp từ lrclib.net.
API miễn phí, không cần key. Trả về LRC format (dòng + timestamp).
Cache local để tránh gọi lại API cho cùng bài hát.
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import requests


@dataclass
class LyricLine:
    """Một dòng lời + timestamp (giây)."""
    time_sec: float
    text: str


@dataclass
class SyncedLyrics:
    """Lời bài hát đã sync."""
    lines: list[LyricLine] = field(default_factory=list)

    def get_current_line(self, elapsed_sec: float) -> Optional[str]:
        """Lấy dòng lyrics hiện tại dựa trên thời gian đã trôi qua (giây)."""
        current = None
        for line in self.lines:
            if line.time_sec <= elapsed_sec:
                current = line.text
            else:
                break
        return current

    @property
    def duration_sec(self) -> float:
        if self.lines:
            return self.lines[-1].time_sec
        return 0

    @property
    def is_empty(self) -> bool:
        return len(self.lines) == 0


class LyricsClient:
    """Fetch synced lyrics từ lrclib.net + cache local."""

    BASE_URL = "https://lrclib.net/api"
    TIMEOUT = 30  # VN network cần timeout cao

    def __init__(self, cache_file: str = ".lyrics_cache"):
        self._cache: dict[str, SyncedLyrics] = {}
        self._cache_file = cache_file
        self._load_cache()

    def _cache_key(self, artist: str, title: str) -> str:
        return f"{artist.lower().strip()}|{title.lower().strip()}"

    def _load_cache(self):
        """Load cache từ file JSON."""
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                for key, lines_data in raw.items():
                    lines = [LyricLine(**l) for l in lines_data]
                    self._cache[key] = SyncedLyrics(lines=lines)
                if self._cache:
                    print(f"[Lyrics] Loaded {len(self._cache)} cached songs from {self._cache_file}")
        except (json.JSONDecodeError, Exception):
            pass

    def _save_cache(self):
        """Lưu cache ra file JSON."""
        try:
            data = {}
            for key, lyrics in self._cache.items():
                if not lyrics.is_empty:  # Chỉ cache bài có lyrics
                    data[key] = [{"time_sec": l.time_sec, "text": l.text} for l in lyrics.lines]
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def fetch(self, artist: str, title: str) -> SyncedLyrics:
        """Lấy synced lyrics. Cache kết quả kể cả 'không tìm thấy'."""
        key = self._cache_key(artist, title)

        if key in self._cache:
            return self._cache[key]

        result = self._do_fetch(artist, title)
        self._cache[key] = result
        if not result.is_empty:
            self._save_cache()
        return result

    def _do_fetch(self, artist: str, title: str) -> SyncedLyrics:
        """Thực hiện API call tới lrclib."""
        # Try 1: GET exact match
        try:
            resp = requests.get(
                f"{self.BASE_URL}/get",
                params={"artist_name": artist, "track_name": title},
                timeout=self.TIMEOUT,
            )

            if resp.status_code == 200:
                data = resp.json()
                synced = data.get("syncedLyrics")
                plain = data.get("plainLyrics")

                if synced:
                    return self._parse_lrc(synced)
                elif plain:
                    return self._plain_to_timed(plain)
                else:
                    return SyncedLyrics()  # Bài có trong DB nhưng chưa ai upload lyrics

            elif resp.status_code == 404:
                # Bài không có trong DB → thử search
                return self._search_and_fetch(artist, title)

        except requests.RequestException as e:
            print(f"   ⚠️ Lỗi mạng khi fetch lyrics: {e}")

        return SyncedLyrics()

    def _search_and_fetch(self, artist: str, title: str) -> SyncedLyrics:
        """Fallback: tìm kiếm bài hát nếu GET trả về 404."""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/search",
                params={"q": f"{artist} {title}"},
                timeout=self.TIMEOUT,
            )

            if resp.status_code == 200:
                results = resp.json()
                if not results:
                    return SyncedLyrics()

                # Lấy bài đầu tiên có synced lyrics
                for item in results:
                    if item.get("syncedLyrics"):
                        return self._parse_lrc(item["syncedLyrics"])

                # Fallback: plain lyrics
                for item in results:
                    if item.get("plainLyrics"):
                        return self._plain_to_timed(item["plainLyrics"])

        except requests.RequestException:
            pass

        return SyncedLyrics()

    @staticmethod
    def _parse_lrc(lrc_text: str) -> SyncedLyrics:
        """Parse LRC format: [mm:ss.xx]text -> list LyricLine."""
        lines = []
        pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")

        for line in lrc_text.strip().split("\n"):
            match = pattern.match(line.strip())
            if match:
                minutes = int(match.group(1))
                seconds = float(match.group(2))
                text = match.group(3).strip()
                if text:
                    lines.append(LyricLine(
                        time_sec=minutes * 60 + seconds,
                        text=text,
                    ))

        lines.sort(key=lambda l: l.time_sec)
        return SyncedLyrics(lines=lines)

    @staticmethod
    def _plain_to_timed(plain_text: str) -> SyncedLyrics:
        """Plain lyrics -> timed giả (5s/dòng) — dùng khi không có LRC."""
        non_empty = [l.strip() for l in plain_text.strip().split("\n") if l.strip()]
        lines = [
            LyricLine(time_sec=i * 5.0, text=text)
            for i, text in enumerate(non_empty)
        ]
        return SyncedLyrics(lines=lines)
