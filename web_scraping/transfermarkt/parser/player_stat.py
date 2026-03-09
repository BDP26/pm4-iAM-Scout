from __future__ import annotations

import re
from collections import Counter

from bs4 import BeautifulSoup

from web_scraping.config import GAMEMINUTE_IMAGES

_RE_MATCH_ID = re.compile(r"/spielbericht/(\d+)")
_RE_CLUB_ID = re.compile(r"/verein/(\d+)")
_RE_SCORE_STRICT = re.compile(r"^\s*(\d+)\s*:\s*(\d+)\s*$")

_RE_MIN_PLAYED = re.compile(r"^\s*(\d{1,3})'\s*$")
_RE_CARD_MINUTES = re.compile(r"\d{1,3}'")
_RE_ANY_INT = re.compile(r"\d+")
_RE_SPIELER_ID = re.compile(r"/spieler/(\d+)")

_RE_UHR = re.compile(
    r"sb-aktion-uhr[^>]*>\s*(\d{1,3})(?:\s*\+\s*(\d{1,2}))?\s*<",
    re.IGNORECASE,
)
_RE_MIN_DOT = re.compile(r"(\d{1,3})(?:\+(\d{1,2}))?\.\s*min\.", re.IGNORECASE)

_RE_BG_POS = re.compile(r"background-position\s*:\s*([-\d]+)px\s+([-\d]+)px", re.IGNORECASE)


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

        dom_ratio = 0.0
        if fuer_clubs:
            c = Counter(fuer_clubs)
            _, top_n = c.most_common(1)[0]
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


def _minute_from_uhr_div(uhr_div) -> int | None:
    if uhr_div is None:
        return None

    base_min = None
    span = uhr_div.select_one('span[style*="background-position"]')
    if span is not None:
        style = (span.get("style") or "").strip()
        m = _RE_BG_POS.search(style)
        if m:
            key = f"{m.group(1)}px {m.group(2)}px"
            base_min = GAMEMINUTE_IMAGES.get(key)

    if base_min is None:
        txt = uhr_div.get_text(" ", strip=True)
        mtxt = _RE_ANY_INT.search(txt)
        if not mtxt:
            return None
        base_min = int(mtxt.group(0))

    txt = uhr_div.get_text(" ", strip=True)
    extra = 0
    mx = re.search(r"\+\s*(\d{1,2})", txt)
    if mx:
        extra = int(mx.group(1))

    minute = int(base_min) + int(extra)
    if minute < 0:
        minute = 0
    if minute > 130:
        minute = 130
    return minute


def _club_id_from_li(li) -> str | None:
    mc = _RE_CLUB_ID.search(str(li))
    return mc.group(1) if mc else None


def parse_spielbericht_goals(html: str) -> list[tuple[int, str]]:
    html = html.replace("\\/", "/")
    soup = BeautifulSoup(html, "lxml")

    out: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()

    lis = soup.select("#sb-tore li")
    if not lis:
        lis = soup.select("div.sb-ereignisse li")

    for li in lis:
        if li.find_parent(id="sb-tore") is None:
            txt = li.get_text(" ", strip=True).lower()
            if "tor" not in txt:
                continue
            if any(w in txt for w in ["wechsel", "auswechsl", "einwechsl", "karte", "gelb", "rot"]):
                continue

        minute = _minute_from_uhr_div(li.select_one(".sb-aktion-uhr"))
        if minute is None:
            continue

        cid = _club_id_from_li(li)
        if not cid:
            continue

        key = (minute, cid)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)

    if out:
        return sorted(out, key=lambda x: x[0])

    out2: list[tuple[int, str]] = []
    seen2: set[tuple[int, str]] = set()

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
        if any(x in wlow for x in ["wechsel", "auswechsl", "einwechsl", "karte", "gelb", "rot"]):
            continue

        mc = _RE_CLUB_ID.search(window)
        if not mc:
            continue
        cid = mc.group(1)

        key = (minute, cid)
        if key in seen2:
            continue
        seen2.add(key)
        out2.append(key)

    return sorted(out2, key=lambda x: x[0])


def _href_to_player_id(href: str | None) -> str | None:
    if not href:
        return None
    m = _RE_SPIELER_ID.search(href)
    return m.group(1) if m else None


def _sort_sub_events(events: list[tuple[int, str]]) -> list[tuple[int, str]]:
    return sorted(events, key=lambda x: (int(x[0]), 0 if x[1] == "off" else 1))


def _extract_sub_event_from_li(li, player_id: str) -> tuple[int, str] | None:
    minute = _minute_from_uhr_div(li.select_one(".sb-aktion-uhr"))
    if minute is None:
        return None

    a_in = li.select_one(".sb-aktion-wechsel-ein a[href*='/spieler/']")
    if a_in is not None:
        pid_in = _href_to_player_id(a_in.get("href"))
        if pid_in == str(player_id):
            return int(minute), "on"

    a_out = li.select_one(".sb-aktion-wechsel-aus a[href*='/spieler/']")
    if a_out is not None:
        pid_out = _href_to_player_id(a_out.get("href"))
        if pid_out == str(player_id):
            return int(minute), "off"

    player_links = li.select('a[href*="/spieler/"]')
    if len(player_links) >= 2:
        ids = [_href_to_player_id(a.get("href")) for a in player_links]
        ids = [x for x in ids if x is not None]

        if len(ids) >= 2:
            if ids[0] == str(player_id):
                return int(minute), "on"
            if ids[1] == str(player_id):
                return int(minute), "off"

    return None


def _extract_sub_event_from_window(window: str, minute: int, player_id: str) -> tuple[int, str] | None:
    ids = re.findall(r"/spieler/(\d+)", window)
    if str(player_id) not in ids:
        return None

    wlow = window.lower()

    ein_match = re.search(
        r'sb-aktion-wechsel-ein.*?href="[^"]*/spieler/(\d+)[^"]*"',
        window,
        re.IGNORECASE | re.DOTALL,
    )
    if ein_match and ein_match.group(1) == str(player_id):
        return int(minute), "on"

    aus_match = re.search(
        r'sb-aktion-wechsel-aus.*?href="[^"]*/spieler/(\d+)[^"]*"',
        window,
        re.IGNORECASE | re.DOTALL,
    )
    if aus_match and aus_match.group(1) == str(player_id):
        return int(minute), "off"

    if len(ids) >= 2:
        if ids[0] == str(player_id):
            return int(minute), "on"
        if ids[1] == str(player_id):
            return int(minute), "off"

    if "einwechsl" in wlow and "auswechsl" not in wlow:
        return int(minute), "on"
    if "auswechsl" in wlow and "einwechsl" not in wlow:
        return int(minute), "off"

    return None


def parse_spielbericht_player_sub_events(html: str, player_id: str) -> list[tuple[int, str]]:
    html = html.replace("\\/", "/")
    soup = BeautifulSoup(html, "lxml")

    out: set[tuple[int, str]] = set()

    lis = soup.select("#sb-wechsel li")
    if not lis:
        lis = soup.select("div.sb-ereignisse li")

    for li in lis:
        ev = _extract_sub_event_from_li(li, player_id)
        if ev is not None:
            out.add((int(ev[0]), ev[1]))

    if out:
        return _sort_sub_events(list(out))

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
        ev = _extract_sub_event_from_window(window, minute, player_id)
        if ev is not None:
            out.add((int(ev[0]), ev[1]))

    return _sort_sub_events(list(out))


def parse_spielbericht_player_sub_minutes(html: str, player_id: str) -> list[int]:
    events = parse_spielbericht_player_sub_events(html, player_id)
    return sorted({int(minute) for minute, _kind in events})


def _minutes_from_intervals(intervals: list[tuple[int, int | None]]) -> int:
    total = 0
    for start, end in intervals:
        end_eff = 90 if end is None else min(int(end), 90)
        total += max(0, end_eff - int(start))
    return int(total)


def _build_appearance_intervals(
    events: list[tuple[int, str]],
    *,
    initial_in: bool,
) -> tuple[list[tuple[int, int | None]], int]:
    intervals: list[tuple[int, int | None]] = []
    ignored = 0

    current_in = bool(initial_in)
    current_start = 0 if current_in else None

    for minute, kind in _sort_sub_events(events):
        minute = max(0, min(130, int(minute)))

        if kind == "on":
            if current_in:
                ignored += 1
                continue
            current_in = True
            current_start = minute
            continue

        if kind == "off":
            if not current_in:
                ignored += 1
                continue
            start = 0 if current_start is None else int(current_start)
            if minute < start:
                minute = start
            intervals.append((start, minute))
            current_in = False
            current_start = None
            continue

        ignored += 1

    if current_in:
        start = 0 if current_start is None else int(current_start)
        intervals.append((start, None))

    return intervals, ignored


def _derive_from_legacy_sub_minutes(
    minutes_played: int | None,
    sub_mins: list[int],
) -> tuple[int, int, int | None, list[tuple[int, int | None]]]:
    in_min = None
    out_min = None

    if minutes_played is None:
        start_11 = 0 if sub_mins else 1
        on = sub_mins[0] if (start_11 == 0 and sub_mins) else 0
        off = None
        intervals = [(int(on), off)] if start_11 == 0 else [(0, off)]
        return int(start_11), int(on), off, intervals

    if sub_mins:
        best = None
        best_kind = None
        best_diff = 10**9

        for m in sub_mins:
            diff_out = abs(int(m) - int(minutes_played))
            diff_in = abs(int(m) - (90 - int(minutes_played)))

            if diff_out <= diff_in and diff_out < best_diff:
                best, best_kind, best_diff = int(m), "out", diff_out
            if diff_in < diff_out and diff_in < best_diff:
                best, best_kind, best_diff = int(m), "in", diff_in

        if best_kind == "out":
            start_11 = 1
            out_min = int(best)
        else:
            start_11 = 0
            in_min = int(best)
    else:
        if int(minutes_played) < 46:
            start_11 = 0
            in_min = max(0, 90 - int(minutes_played))
        else:
            start_11 = 1

    on = 0 if start_11 == 1 else (int(in_min) if in_min is not None else max(0, 90 - int(minutes_played)))
    off = out_min if out_min is not None else (int(minutes_played) if start_11 == 1 and int(minutes_played) < 90 else None)

    if off is not None and off < on:
        off = max(90, on)

    intervals = [(int(on), None if off is None else int(off))]
    return int(start_11), int(on), (None if off is None else int(off)), intervals


def derive_start11_onoff_and_intervals(
    minutes_played: int | None,
    sub_events: list[tuple[int, str]] | list[int],
) -> tuple[int, int, int | None, list[tuple[int, int | None]]]:
    if not sub_events:
        return _derive_from_legacy_sub_minutes(minutes_played, [])

    first = sub_events[0]
    if not isinstance(first, tuple):
        legacy_mins = sorted({int(m) for m in sub_events})
        return _derive_from_legacy_sub_minutes(minutes_played, legacy_mins)

    events = []
    for minute, kind in sub_events:
        if kind not in {"on", "off"}:
            continue
        minute = max(0, min(130, int(minute)))
        events.append((minute, kind))

    if not events:
        return _derive_from_legacy_sub_minutes(minutes_played, [])

    events = _sort_sub_events(list(set(events)))

    if minutes_played is None:
        initial_in = events[0][1] == "off"
        intervals, _ignored = _build_appearance_intervals(events, initial_in=initial_in)
    else:
        candidates = []
        for initial_in in (True, False):
            intervals, ignored = _build_appearance_intervals(events, initial_in=initial_in)
            played_guess = _minutes_from_intervals(intervals)

            first_event_penalty = 0
            if initial_in and events[0][1] == "on":
                first_event_penalty += 1
            if (not initial_in) and events[0][1] == "off":
                first_event_penalty += 1

            candidates.append(
                (
                    abs(int(minutes_played) - int(played_guess)),
                    ignored,
                    first_event_penalty,
                    0 if initial_in else 1,
                    intervals,
                )
            )

        _diff, _ignored, _penalty, _starter_pref, intervals = min(
            candidates,
            key=lambda x: (x[0], x[1], x[2], x[3]),
        )

    if not intervals:
        return _derive_from_legacy_sub_minutes(minutes_played, [])

    start_11 = 1 if int(intervals[0][0]) == 0 else 0
    on_min = int(intervals[0][0])
    off_min = intervals[-1][1]

    return int(start_11), int(on_min), (None if off_min is None else int(off_min)), intervals


def derive_start11_onoff(
    minutes_played: int | None,
    sub_events: list[tuple[int, str]] | list[int],
) -> tuple[int, int, int]:
    start_11, on_min, off_min, _intervals = derive_start11_onoff_and_intervals(minutes_played, sub_events)
    off_out = 90 if off_min is None else int(off_min)
    return int(start_11), int(on_min), int(off_out)