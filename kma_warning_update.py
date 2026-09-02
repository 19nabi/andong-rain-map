import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

URL = "https://www.weather.go.kr/w/wnuri-fct2021/weather/today-warning.do"
OUT_FILE = "warning.json"

headers = {
    "User-Agent": "Mozilla/5.0"
}

result = {
    "active": False,
    "level": None,
    "area": None,
    "announce_time": None,
    "effective_time": None,
    "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

print("기상청 안동 호우특보 확인 중...")

try:
    r = requests.get(
        URL,
        headers=headers,
        timeout=20
    )

    r.raise_for_status()

    soup = BeautifulSoup(
        r.text,
        "html.parser"
    )

    text = soup.get_text(
        " ",
        strip=True
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    # 발표시각
    announce_match = re.search(
        r"발표시각\s*:\s*(.+?)\s*발효시각",
        text
    )

    # 발효시각
    effective_match = re.search(
        r"발효시각\s*:\s*(.+?)\s*(?:특보 내용|o )",
        text
    )

    announce_time = (
        announce_match.group(1).strip()
        if announce_match
        else None
    )

    effective_time = (
        effective_match.group(1).strip()
        if effective_match
        else None
    )

    # 현재 발효 특보 부분
    start = text.find("특보 내용")
    end = text.find("예비특보 현황")

    if start >= 0:
        if end > start:
            warning_text = text[start:end]
        else:
            warning_text = text[start:]
    else:
        warning_text = ""

    patterns = [
        (
            "호우경보",
            r"호우경보\s*:\s*(.+?)(?=\s+o\s+|<참고사항>|$)"
        ),
        (
            "호우주의보",
            r"호우주의보\s*:\s*(.+?)(?=\s+o\s+|<참고사항>|$)"
        )
    ]

    for level, pattern in patterns:

        match = re.search(
            pattern,
            warning_text
        )

        if not match:
            continue

        areas = match.group(1).strip()

        if "안동" in areas:

            area_match = re.search(
                r"[^,()]*안동[^,()]*",
                areas
            )

            if area_match:
                area = area_match.group(0).strip()
            else:
                area = "안동"

            result = {
                "active": True,
                "level": level,
                "area": area,
                "announce_time": announce_time,
                "effective_time": effective_time,
                "checked_at": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            }

            break

except Exception as e:

    print("특보 확인 오류:", e)

    result["error"] = str(e)


with open(
    OUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )


if result["active"]:

    print("호우특보 감지:", result["level"])
    print("대상:", result["area"])

else:

    print("현재 안동 호우특보 없음")


print("저장:", OUT_FILE)