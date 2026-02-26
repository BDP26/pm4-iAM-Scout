# web_scraping/transfermarkt/parser/player_stat.py
from __future__ import annotations

import re
from collections import Counter
from bs4 import BeautifulSoup

_RE_MATCH_ID = re.compile(r"/spielbericht/(\d+)")
_RE_CLUB_ID = re.compile(r"/verein/(\d+)")
_RE_SCORE_STRICT = re.compile(r"^\s*(\d+)\s*:\s*(\d+)\s*$")

_RE_MIN_PLAYED = re.compile(r"^\s*(\d{1,3})'\s*$")
_RE_CARD_MINUTES = re.compile(r"\d{1,3}'")
_RE_ANY_INT = re.compile(r"\d+")

_RE_UHR = re.compile(
    r"sb-aktion-uhr[^>]*>\s*(\d{1,3})(?:\s*\+\s*(\d{1,2}))?\s*<",
    re.IGNORECASE,
)
_RE_MIN_DOT = re.compile(r"(\d{1,3})(?:\+(\d{1,2}))?\.\s*min\.", re.IGNORECASE)


def _cell_to_count(td) -> int:
    if td is None:
        return 0
    txt = td.get_text(" ", strip=True)
    if not txt:
        return 0
    mins = _RE_CARD_MINUTES.findall(txt)
    if mins:
        return len(mins)
    m = _RE_ANY_INT.search(txt)
    return int(m.group(0)) if m else 0


def _analyze_tables(soup: BeautifulSoup) -> list[dict]:
    out = []
    tables = soup.select("table")
    for idx, t in enumerate(tables):
        heads = [th.get_text(" ", strip=True).lower() for th in t.select("thead th")]
        has_fuer = any("für" in h for h in heads)
        has_erg = any("ergebnis" in h for h in heads)
        links = t.select('tbody a[href*="spielbericht/"]')

        fuer_clubs = []
        for tr in t.select("tbody tr"):
            clubs = _RE_CLUB_ID.findall(str(tr))
            if clubs:
                fuer_clubs.append(clubs[0])

        top_club = None
        dom_ratio = 0.0
        if fuer_clubs:
            c = Counter(fuer_clubs)
            top_club, top_n = c.most_common(1)[0]
            dom_ratio = top_n / max(1, len(fuer_clubs))

        score = (3 if has_fuer else 0) + (2 if has_erg else 0) + min(6, len(links) / 8) + dom_ratio
        out.append({"idx": idx, "score": score})
    return sorted(out, key=lambda x: x["score"], reverse=True)


def parse_player_leistungsdaten(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    tables = soup.select("table")
    if not tables:
        return []

    analyses = _analyze_tables(soup)
    table = tables[analyses[0]["idx"]] if analyses else tables[0]

    heads = [th.get_text(" ", strip=True) for th in table.select("thead th")]
    heads_l = [h.lower() for h in heads]
    idx_fuer = None
    for i, h in enumerate(heads_l):
        if "für" in h:
            idx_fuer = i
            break

    out: list[dict] = []

    for tr in table.select("tbody tr"):
        tds = tr.find_all("td", recursive=False)
        if not tds:
            continue

        a = tr.select_one('a[href*="spielbericht/"]')
        if not a or not a.get("href"):
            continue

        href = (a.get("href") or "").strip()
        m = _RE_MATCH_ID.search(href)
        if not m:
            continue
        match_id = m.group(1)

        club_id = None
        if idx_fuer is not None and idx_fuer < len(tds):
            mc = _RE_CLUB_ID.search(str(tds[idx_fuer]))
            if mc:
                club_id = mc.group(1)
        if club_id is None:
            clubs = _RE_CLUB_ID.findall(str(tr))
            club_id = clubs[0] if clubs else None

        minuten = None
        minutes_idx = None
        for j in range(len(tds) - 1, -1, -1):
            mmp = _RE_MIN_PLAYED.match(tds[j].get_text(" ", strip=True))
            if mmp:
                minuten = int(mmp.group(1))
                minutes_idx = j
                break

        tore = assists = gelb = gelb_rot = rot = 0
        if minutes_idx is not None and minutes_idx >= 5:
            tore = _cell_to_count(tds[minutes_idx - 5])
            assists = _cell_to_count(tds[minutes_idx - 4])
            gelb = _cell_to_count(tds[minutes_idx - 3])
            gelb_rot = _cell_to_count(tds[minutes_idx - 2])
            rot = _cell_to_count(tds[minutes_idx - 1])
        else:
            if len(tds) >= 6:
                tore = _cell_to_count(tds[-6])
                assists = _cell_to_count(tds[-5])
                gelb = _cell_to_count(tds[-4])
                gelb_rot = _cell_to_count(tds[-3])
                rot = _cell_to_count(tds[-2])

        out.append(
            {
                "match_id": match_id,
                "match_href": href,
                "club_id": club_id,
                "tore": int(tore),
                "assists": int(assists),
                "gelb": int(gelb),
                "gelb_rot": int(gelb_rot),
                "rot": int(rot),
                "minuten": minuten,
            }
        )

    return out


def parse_spielbericht_goals(html: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    seen = set()

    # Transfermarkt kann \/ enthalten
    html = html.replace("\\/", "/")

    def iter_windows():
        for m in _RE_UHR.finditer(html):
            base = int(m.group(1))
            extra = int(m.group(2)) if m.group(2) else 0
            minute = base + extra
            start = max(0, m.start() - 900)
            end = min(len(html), m.end() + 900)
            yield minute, html[start:end]
        low = html.lower()
        for m in _RE_MIN_DOT.finditer(low):
            base = int(m.group(1))
            extra = int(m.group(2)) if m.group(2) else 0
            minute = base + extra
            start = max(0, m.start() - 900)
            end = min(len(low), m.end() + 900)
            yield minute, html[start:end]

    for minute, window in iter_windows():
        wlow = window.lower()
        if "tor" not in wlow:
            continue
        if "wechsel" in wlow or "auswechsl" in wlow or "einwechsl" in wlow:
            continue
        if "karte" in wlow or "gelb" in wlow or "rote karte" in wlow or " rot" in wlow:
            continue

        mc = _RE_CLUB_ID.search(window)
        if not mc:
            continue
        cid = mc.group(1)

        key = (minute, cid)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)

    return sorted(out, key=lambda x: x[0])


def parse_spielbericht_player_sub_minutes(html: str, player_id: str) -> list[int]:
    html = html.replace("\\/", "/")
    pid_pat = re.compile(rf"/profil/spieler/{re.escape(player_id)}")
    mins = set()

    def iter_windows():
        for m in _RE_UHR.finditer(html):
            base = int(m.group(1))
            extra = int(m.group(2)) if m.group(2) else 0
            minute = base + extra
            start = max(0, m.start() - 900)
            end = min(len(html), m.end() + 900)
            yield minute, html[start:end]
        low = html.lower()
        for m in _RE_MIN_DOT.finditer(low):
            base = int(m.group(1))
            extra = int(m.group(2)) if m.group(2) else 0
            minute = base + extra
            start = max(0, m.start() - 900)
            end = min(len(low), m.end() + 900)
            yield minute, html[start:end]

    for minute, window in iter_windows():
        wlow = window.lower()
        if ("wechsel" not in wlow) and ("auswechsl" not in wlow) and ("einwechsl" not in wlow):
            continue
        if not pid_pat.search(window):
            continue
        mins.add(minute)

    return sorted(mins)


def derive_start11_onoff(minutes_played: int | None, sub_mins: list[int]) -> tuple[int, int, int]:
    in_min = None
    out_min = None

    if minutes_played is None:
        start_11 = 0 if sub_mins else 1
        on = sub_mins[0] if (start_11 == 0 and sub_mins) else 0
        off = 90
        return start_11, int(on), int(off)

    if sub_mins:
        best = None
        best_kind = None
        best_diff = 10**9

        for m in sub_mins:
            diff_out = abs(m - minutes_played)
            diff_in = abs(m - (90 - minutes_played))
            if diff_out <= diff_in and diff_out < best_diff:
                best, best_kind, best_diff = m, "out", diff_out
            if diff_in < diff_out and diff_in < best_diff:
                best, best_kind, best_diff = m, "in", diff_in

        if best_kind == "out":
            start_11 = 1
            out_min = best
        else:
            start_11 = 0
            in_min = best
    else:
        if minutes_played < 46:
            start_11 = 0
            in_min = max(0, 90 - minutes_played)
        else:
            start_11 = 1

    on = 0 if start_11 == 1 else (in_min if in_min is not None else max(0, 90 - minutes_played))
    off = out_min if out_min is not None else (minutes_played if start_11 == 1 and minutes_played < 90 else 90)

    if off < on:
        off = max(90, on)

    return int(start_11), int(on), int(off)