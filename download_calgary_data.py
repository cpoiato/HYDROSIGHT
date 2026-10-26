#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HydroSight: download real Calgary datasets to data/raw. Python standard library only.
Put this file in repository root and press Run in PyCharm.
Existing raw files are preserved; new successful downloads receive UTC snapshot names.
"""
import csv
import hashlib
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
STATION_ID = 50430  # Current weather station; preserved for original downloads
HISTORICAL_STATION_ID = 2205  # Calgary Intl Airport historical station
FIRST_YEAR = 2010
LAST_YEAR = 2026
HISTORY_FIRST_YEAR = 1960
HISTORY_LAST_YEAR = 2009
SOCRATA = "https://data.calgary.ca/resource"
ARCGIS = "https://services1.arcgis.com/AVP60cs0Q9PEA8rH/ArcGIS/rest/services"
ECCC = "https://climate.weather.gc.ca/climate_data/bulk_data_e.html"
PAGE_SIZE = 1000


def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def fetch(url, query=None, tries=3):
    if query:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(query)
    error = None
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "HydroSight-Academic/1.0", "Accept": "*/*"})
            with urllib.request.urlopen(request, timeout=70) as response:
                payload = response.read()
            if not payload:
                raise ValueError("Empty response")
            return payload
        except Exception as exc:
            error = exc
            if attempt + 1 < tries:
                log(f"  Retry {attempt + 1}/{tries}: {exc}")
                time.sleep(attempt + 2)
    raise RuntimeError(f"Request failed: {url}: {error}")


def fetch_json(url, query):
    data = json.loads(fetch(url, query).decode("utf-8-sig"))
    if isinstance(data, dict) and "error" in data:
        raise ValueError(f"Remote API error: {data['error']}")
    return data


def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_entry(path, count, source, **extra):
    return {"status": "OK", "filename": str(path.relative_to(ROOT)), "records": count,
            "sha256": sha256(path), "bytes": path.stat().st_size, "source": source, **extra}


def download_socrata(dataset_id, subfolder, basename, snapshot):
    directory = RAW / subfolder
    directory.mkdir(parents=True, exist_ok=True)
    endpoint = f"{SOCRATA}/{dataset_id}.json"
    count_result = fetch_json(endpoint, {"$select": "count(*)"})
    total = int(count_result[0]["count"])
    path = directory / f"{basename}_{snapshot}.jsonl"
    if path.exists():
        raise FileExistsError(f"Snapshot already exists: {path}")
    temp = path.with_name(path.name + ".part")
    got = 0
    log(f"{basename}: expecting {total:,} records")
    try:
        with temp.open("w", encoding="utf-8") as stream:
            for offset in range(0, total, PAGE_SIZE):
                batch = fetch_json(endpoint, {"$limit": PAGE_SIZE, "$offset": offset,
                                              "$order": ":id ASC"})
                if not isinstance(batch, list) or len(batch) != min(PAGE_SIZE, total-offset):
                    raise ValueError(f"Incomplete page at {offset}: got {len(batch) if isinstance(batch,list) else type(batch)}")
                for item in batch:
                    stream.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
                got += len(batch)
                if got % 5000 == 0 or got == total:
                    log(f"  {got:,}/{total:,}")
        if got != total:
            raise ValueError(f"Count changed during extraction: got {got}, expected {total}")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return make_entry(path, got, endpoint, snapshot_utc=snapshot,
                      note="Snapshot of current published records, not proof of historic availability")


def download_arcgis(service, subfolder, basename, snapshot):
    layer = f"{ARCGIS}/{service}/FeatureServer/0"
    info = fetch_json(layer, {"f": "json"})
    oid = info.get("objectIdField") or "OBJECTID"
    count = fetch_json(layer + "/query", {"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
    if not isinstance(count, int):
        raise ValueError("ArcGIS count missing")
    limit = min(int(info.get("maxRecordCount") or 1000), 1000)
    features = []
    log(f"{basename}: expecting {count} records")
    for offset in range(0, count, limit):
        data = fetch_json(layer + "/query", {"where": "1=1", "outFields": "*",
                      "returnGeometry": "true", "outSR": 4326, "f": "geojson",
                      "orderByFields": f"{oid} ASC", "resultOffset": offset,
                      "resultRecordCount": min(limit, count-offset)})
        batch = data.get("features")
        if not isinstance(batch, list) or len(batch) != min(limit, count-offset):
            raise ValueError(f"ArcGIS page incomplete at {offset}")
        features.extend(batch)
        log(f"  {len(features)}/{count}")
    ids = [str(item.get("properties", {}).get(oid)) for item in features]
    if len(set(ids)) != count or "None" in ids:
        raise ValueError("Duplicate/missing ArcGIS OBJECTIDs")
    invalid = sum(not isinstance(x.get("geometry"),dict) or x["geometry"].get("type") != "Point" or
                  not isinstance(x["geometry"].get("coordinates"),list) or len(x["geometry"]["coordinates"]) < 2
                  for x in features)
    path = RAW / subfolder / f"{basename}_{snapshot}.geojson"
    save_json(path, {"type": "FeatureCollection", "features": features})
    return make_entry(path, count, layer, invalid_geometries=invalid,
                      note="Current facility locations only, excluded from historical ML features")


def climate_date(row):
    for key, val in row.items():
        normalized = (key or "").lower().replace(" ", "").replace("/", "").replace("_", "")
        if normalized in ("datetime", "dateheure", "date", "datetimeutc") and val:
            s = str(val).strip()[:10]
            try:
                datetime.strptime(s, "%Y-%m-%d")
                return s
            except ValueError:
                pass
    return None


def number(value):
    if value is None or str(value).strip() in ("", "M", "NA", "Trace", "T"):
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return None


def field(row, names):
    def norm(s):
        return s.lower().replace(" ", "").replace("_", "").replace("(", "").replace(")", "").replace("°", "")
    normalized = {norm(k): v for k, v in row.items() if k}
    for name in names:
        if norm(name) in normalized:
            return number(normalized[norm(name)])
    return None


def download_weather(snapshot, first_year=FIRST_YEAR, last_year=LAST_YEAR, station_id=STATION_ID):
    directory = RAW / "weather"
    directory.mkdir(parents=True, exist_ok=True)
    yearly, failures, coverage, data = [], {}, {}, []
    for year in range(first_year, last_year + 1):
        path = directory / f"daily_weather_eccc_{station_id}_{year}_{snapshot}.csv"
        try:
            log(f"weather: {year}")
            payload = fetch(ECCC, {"format": "csv", "stationID": station_id,
                                   "Year": year, "Month": 1, "Day": 1,
                                   "timeframe": 2, "submit": "Download Data"})
            if payload.lstrip()[:20].lower().startswith((b"<html", b"<!doctype html")):
                raise ValueError("ECCC sent HTML instead of CSV")
            text = payload.decode("utf-8-sig", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            headers = reader.fieldnames or []
            if not headers or not any("date" in (x or "").lower() for x in headers):
                raise ValueError(f"Unexpected climate headers: {headers[:8]}")
            rows = list(reader)
            selected = []
            for row in rows:
                dt = climate_date(row)
                if dt and dt.startswith(str(year)):
                    selected.append({"date": dt, "station_id": station_id,
                        "temp_mean_c": field(row, ["Mean Temp (°C)", "Mean Temp (C)", "Température moy. (°C)" ]),
                        "temp_min_c": field(row, ["Min Temp (°C)", "Min Temp (C)", "Température min. (°C)"]),
                        "temp_max_c": field(row, ["Max Temp (°C)", "Max Temp (C)", "Température max. (°C)"]),
                        "precip_mm": field(row, ["Total Precip (mm)", "Total Precipitation (mm)"]),
                        "snow_cm": field(row, ["Total Snow (cm)"])})
            if not selected:
                raise ValueError("No observations for expected year")
            if not any(any(r[k] is not None for k in ("temp_mean_c", "temp_min_c", "temp_max_c")) for r in selected):
                raise ValueError("No measured temperature values for expected year")
            if path.exists():
                raise FileExistsError(f"Snapshot already exists: {path}")
            temp = path.with_name(path.name + ".part")
            try:
                temp.write_bytes(payload)
                os.replace(temp, path)
            finally:
                temp.unlink(missing_ok=True)
            yearly.append(make_entry(path, len(selected), ECCC, station_id=station_id, year=year))
            coverage[str(year)] = {"days": len(set(r["date"] for r in selected)),
                                   "min_temp_days": sum(r["temp_min_c"] is not None for r in selected),
                                   "max_temp_days": sum(r["temp_max_c"] is not None for r in selected),
                                   "precip_days": sum(r["precip_mm"] is not None for r in selected),
                                   "snow_days": sum(r["snow_cm"] is not None for r in selected)}
            data.extend(selected)
            log(f"  {len(selected)} daily rows, min temp: {coverage[str(year)]['min_temp_days']}")
        except Exception as exc:
            failures[str(year)] = str(exc)
            log(f"  FAILED {year}: {exc}")
    combined = None
    if data:
        combined = directory / f"daily_weather_calgary_{first_year}_{last_year}_{snapshot}.csv"
        if combined.exists():
            raise FileExistsError(f"Snapshot already exists: {combined}")
        temp = combined.with_name(combined.name + ".part")
        try:
            with temp.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["date", "station_id", "temp_mean_c", "temp_min_c",
                                                              "temp_max_c", "precip_mm", "snow_cm"])
                writer.writeheader()
                writer.writerows(sorted(data, key=lambda x: x["date"]))
            os.replace(temp, combined)
        finally:
            temp.unlink(missing_ok=True)
    return {"status": "OK" if not failures else "PARTIAL", "source": ECCC,
            "station_id": station_id, "records": len(data), "annual_files": yearly,
            "combined_file": str(combined.relative_to(ROOT)) if combined else None,
            "annual_coverage": coverage, "failed_years": failures,
            "note": "Observed climate from the forecast horizon must NEVER be used as predictor"}


def main():
    historical_only = "--all" not in sys.argv[1:]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for folder in ("water_breaks", "pipes", "weather", "hospitals", "schools"):
        (RAW / folder).mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    manifest = {"run_utc": datetime.now(timezone.utc).isoformat(), "snapshot": stamp,
                "project": "HydroSight", "sources": {}, "errors": {},
                "caution": "Data collection does not certify absence of temporal leakage or future update cadence."}
    tasks = [("water_breaks", lambda: download_socrata("dpcu-jr23", "water_breaks", "water_main_breaks", stamp)),
             ("pipes", lambda: download_socrata("w6h9-w33i", "pipes", "public_water_mains", stamp)),
             ("hospitals", lambda: download_arcgis("Hospital", "hospitals", "hospitals", stamp)),
             ("schools", lambda: download_arcgis("School", "schools", "schools", stamp)),
             ("weather", lambda: download_weather(stamp))]
    if historical_only:
        tasks = [("weather_history", lambda: download_weather(
            stamp, HISTORY_FIRST_YEAR, HISTORY_LAST_YEAR, HISTORICAL_STATION_ID))]
    log("HydroSight — historical weather download" if historical_only else "HydroSight — real dataset download")
    log(f"Target: {RAW}")
    if historical_only:
        log("Downloading ONLY ECCC climate history, 1960–2009; other datasets untouched")
    for name, action in tasks:
        try:
            manifest["sources"][name] = action()
            log(f"COMPLETED: {name}")
        except Exception as exc:
            manifest["errors"][name] = f"{type(exc).__name__}: {exc}"
            log(f"FAILED: {name}: {exc}")
    report_path = REPORTS / f"download_{'weather_history_' if historical_only else 'manifest_'}{stamp}.json"
    save_json(report_path, manifest)
    if not historical_only:
        latest = REPORTS / "latest_download_manifest.json"
        save_json(latest, manifest)
    log(f"Manifest: {report_path}")
    log(f"Sources completed: {len(manifest['sources'])}/{len(tasks)}; failed: {len(manifest['errors'])}")
    if manifest["errors"] or any(entry.get("status") != "OK" for entry in manifest["sources"].values()):
        log("Some sources failed or historical weather coverage is partial. Read the manifest; valid downloads are preserved.")
        sys.exit(1)
    log("Historical weather finished." if historical_only else "All five sources downloaded. Next step: EDA (no model training performed).")


if __name__ == "__main__":
    main()
