"""
Mood Detector — phân tích lyrics tiếng Việt để đoán mood bài hát.
Dùng keyword matching: đếm từ khóa trong lyrics, chọn mood có nhiều match nhất.
"""

# Map mood → emoji, kèm từ khóa tiếng Việt
MOOD_MAP = {
    "buồn": {
        "emoji": "😢",
        "keywords": [
            "buồn", "khóc", "nước mắt", "chia tay", "xa cách",
            "cô đơn", "đau", "tiếc nuối", "giá như", "ước gì",
            "lỡ", "mất", "xa", "rời xa", "tạm biệt", "lặng",
            "thở dài", "lẻ loi", "một mình", "lạc", "cuối",
        ],
    },
    "yêu": {
        "emoji": "💕",
        "keywords": [
            "yêu", "thương", "nhớ", "hôn", "ôm", "bên nhau",
            "hạnh phúc", "ngọt ngào", "say đắm", "tim", "lòng",
            "chờ", "đợi", "mãi", "trọn đời", "cưới", "gần",
            "bên cạnh", "tay nắm", "chung đôi", "phút giây",
        ],
    },
    "sôi động": {
        "emoji": "🔥",
        "keywords": [
            "quẩy", "nhảy", "bay", "cháy", "điên", "say",
            "bùng nổ", "mạnh", "lên", "nóng", "beat", "drop",
            "sàn", "club", "party", "tiệc", "đêm nay",
            "phá cách", "chất", "ngầu", "swag",
        ],
    },
    "chill": {
        "emoji": "🌊",
        "keywords": [
            "chill", "bình yên", "thư giãn", "nhẹ nhàng",
            "lững lờ", "trôi", "gió", "nắng", "chiều",
            "hoàng hôn", "bình minh", "sáng", "mây", "trời",
            "biển", "sóng", "cát", "phố", "dạo",
        ],
    },
    "tâm trạng": {
        "emoji": "🥀",
        "keywords": [
            "tâm trạng", "suy tư", "trầm", "lắng", "lỡ làng",
            "duyên phận", "số phận", "lỡ duyên", "thanh xuân",
            "kỷ niệm", "ngày xưa", "quá khứ", "hồi ức",
            "tiếc", "vỡ", "tan", "phai", "nhạt",
        ],
    },
    "vui": {
        "emoji": "🎉",
        "keywords": [
            "vui", "cười", "hát", "hân hoan", "rạng rỡ",
            "tuyệt vời", "tốt đẹp", "hồ hởi", "phấn khởi",
            "tự hào", "vinh quang", "chiến thắng", "thành công",
        ],
    },
    "rap": {
        "emoji": "🎤",
        "keywords": [
            "rap", "flow", "verse", "mic", "bar",
            "track", "rhyme", "beat", "bass", "hiphop",
            "underground", "diss", "real", "game",
        ],
    },
}


def detect_mood(lyrics_text: str) -> str:
    """Phân tích lyrics, trả về emoji phù hợp nhất."""
    if not lyrics_text:
        return "🎵"  # Default

    text_lower = lyrics_text.lower()
    scores = {}

    for mood, info in MOOD_MAP.items():
        score = 0
        for kw in info["keywords"]:
            # Đếm số lần xuất hiện của keyword trong lyrics
            score += text_lower.count(kw)
        if score > 0:
            scores[mood] = score

    if not scores:
        return "🎵"

    # Chọn mood có score cao nhất
    best_mood = max(scores, key=scores.get)
    return MOOD_MAP[best_mood]["emoji"]
