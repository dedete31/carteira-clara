#!/usr/bin/env python3
"""Download the latest daily B3 COTAHIST ZIP and keep a compact quote index."""

from __future__ import annotations

import json
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "data" / "quotes.json"
BASE_URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_D{}.ZIP"
MAX_ZIP_SIZE = 100 * 1024 * 1024


def load_feed() -> dict:
    if not FEED.exists():
        return {"schemaVersion": 1, "source": "B3 COTAHIST", "sourceDate": None, "generatedAt": None, "quotes": {}}
    return json.loads(FEED.read_text(encoding="utf-8"))


def download_daily(day: datetime, destination: Path) -> bool:
    filename_date = day.strftime("%d%m%Y")
    request = urllib.request.Request(
        BASE_URL.format(filename_date),
        headers={
            "User-Agent": "CarteiraClara/1.0 (daily COTAHIST importer)",
            "Accept": "application/zip, application/octet-stream, */*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response, destination.open("wb") as output:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_ZIP_SIZE:
                    raise RuntimeError("O ZIP diário excedeu o limite de segurança de 100 MB.")
                output.write(chunk)
        return destination.stat().st_size > 0
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise RuntimeError(f"B3 respondeu HTTP {exc.code} ao buscar o COTAHIST de {filename_date}.") from exc


def parse_daily(zip_path: Path) -> tuple[dict[str, dict], str | None]:
    quotes: dict[str, dict] = {}
    latest_date = None
    with zipfile.ZipFile(zip_path) as archive:
        text_files = [name for name in archive.namelist() if name.lower().endswith(".txt")]
        if not text_files:
            raise RuntimeError("O ZIP da B3 não contém o TXT COTAHIST esperado.")
        text_name = next((name for name in text_files if "cotahist" in name.lower()), text_files[0])
        with archive.open(text_name) as text_file:
            for raw in text_file:
                row = raw.rstrip(b"\r\n")
                if len(row) < 121 or row[0:2] != b"01":
                    continue
                day = row[2:10].decode("ascii", errors="ignore")
                symbol = row[12:24].decode("ascii", errors="ignore").strip().upper()
                market = row[24:27].decode("ascii", errors="ignore")
                try:
                    close_cents = int(row[108:121])
                except ValueError:
                    continue
                if len(day) != 8 or not symbol or close_cents <= 0:
                    continue
                latest_date = max(latest_date or day, day)
                current = quotes.get(symbol)
                if not current or day > current["date"] or (
                    day == current["date"] and market == "010" and current["market"] != "010"
                ):
                    quotes[symbol] = {"price": round(close_cents / 100, 2), "date": day, "market": market}
    return quotes, latest_date


def main() -> int:
    feed = load_feed()
    quotes = feed.get("quotes", {})
    today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    with tempfile.TemporaryDirectory(prefix="cotahist-") as temp_dir:
        zip_path = Path(temp_dir) / "cotahist.zip"
        imported = None
        for offset in range(8):
            candidate = datetime.combine(today - timedelta(days=offset), datetime.min.time())
            if not download_daily(candidate, zip_path):
                continue
            daily_quotes, file_date = parse_daily(zip_path)
            if daily_quotes and file_date:
                imported = (daily_quotes, file_date, candidate.strftime("%d%m%Y"))
                break
    if not imported:
        print("A B3 não publicou um arquivo diário novo nos últimos 8 dias; mantendo o último feed.")
        return 0

    daily_quotes, file_date, downloaded_date = imported
    updated = 0
    for symbol, quote in daily_quotes.items():
        previous = quotes.get(symbol)
        if not previous or quote["date"] >= previous.get("date", ""):
            quotes[symbol] = {"price": quote["price"], "date": quote["date"]}
            updated += 1

    previous_date = feed.get("sourceDate") or ""
    source_date = max(previous_date, file_date)
    changed = source_date != previous_date or quotes != feed.get("quotes", {})
    if not changed:
        print(f"COTAHIST de {downloaded_date} já está processado; nenhuma alteração.")
        return 0

    output = {
        "schemaVersion": 1,
        "source": "B3 COTAHIST",
        "sourceDate": source_date,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "quotes": quotes,
    }
    FEED.parent.mkdir(parents=True, exist_ok=True)
    FEED.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Importado COTAHIST {downloaded_date}: {updated} registros, {len(quotes)} tickers no feed; pregão {source_date}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError, RuntimeError) as exc:
        print(f"Falha ao atualizar COTAHIST: {exc}", file=sys.stderr)
        raise SystemExit(1)
