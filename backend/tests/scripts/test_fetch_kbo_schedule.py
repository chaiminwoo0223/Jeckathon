from scripts.fetch_kbo_schedule import parse_rows


def _row(*cells: tuple[str, str | None]) -> dict:
    return {"row": [{"Text": text, "Class": cls} for text, cls in cells]}


def _play(away: str, home: str, scores: tuple[int, int] | None = None) -> str:
    if scores is None:
        return f"<span>{away}</span><em><span>vs</span></em><span>{home}</span>"
    a, h = scores
    return (
        f'<span>{away}</span><em><span class="win">{a}</span><span>vs</span>'
        f'<span class="lose">{h}</span></em><span>{home}</span>'
    )


def test_parse_rows_carries_date_and_reads_away_vs_home() -> None:
    rows = [
        _row(
            ("07.01(수)", "day"),
            ("<b>18:30</b>", "time"),
            (_play("롯데", "두산", (5, 2)), "play"),
            ("", "relay"),
            ("잠실", None),
            ("-", None),
        ),
        _row(
            ("<b>18:30</b>", "time"),
            (_play("NC", "한화"), "play"),
            ("", "relay"),
            ("대전", None),
            ("우천취소", None),
        ),
        _row(
            ("<b>14:00</b>", "time"),
            (_play("KT", "삼성", (1, 12)), "play"),
            ("", "relay"),
            ("대구", None),
            ("KS 5차전", None),
        ),
    ]
    games = parse_rows(rows, 2026, "regular")

    assert len(games) == 2  # 우천취소 dropped
    first, second = games
    assert first == {
        "kickoff_at": "2026-07-01T18:30:00+09:00",
        "home": "두산",
        "away": "롯데",
        "home_score": 2,
        "away_score": 5,
        "venue": "잠실",
        "round_label": "",
        "series": "regular",
    }
    # no date cell: same day as the previous row
    assert second["kickoff_at"] == "2026-07-01T14:00:00+09:00"
    assert (second["home"], second["home_score"]) == ("삼성", 12)
    assert second["round_label"] == "KS 5차전"


def test_parse_rows_keeps_unplayed_future_game() -> None:
    rows = [
        _row(
            ("03.25(목)", "day"),
            ("<b>18:30</b>", "time"),
            (_play("LG", "KIA"), "play"),
            ("", "relay"),
            ("광주", None),
            ("-", None),
        )
    ]
    (game,) = parse_rows(rows, 2027, "regular")
    assert game["home_score"] is None and game["away_score"] is None
    assert game["home"] == "KIA"
