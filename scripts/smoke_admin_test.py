#!/usr/bin/env python3
"""Simple smoke tester for admin endpoints.

Requires the FastAPI app to be running locally at http://127.0.0.1:8000

Usage:
    python scripts/smoke_admin_test.py

This prints current view, toggles binance to live, and shows curl examples.
"""
import httpx

BASE = "http://127.0.0.1:8000"


def get_view():
    r = httpx.get(f"{BASE}/admin/view-environment", timeout=10.0)
    print("GET /admin/view-environment ->", r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)


def toggle(market: str, view: str):
    r = httpx.post(f"{BASE}/admin/toggle-view", params={"market": market, "view": view}, timeout=10.0)
    print(f"POST /admin/toggle-view?market={market}&view={view} ->", r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)


def curl_examples():
    print("\nCURL examples:")
    print(f"curl -s {BASE}/admin/view-environment|jq")
    print(f"curl -X POST '{BASE}/admin/toggle-view?market=binance&view=sandbox'")


if __name__ == "__main__":
    print("== Smoke test: admin endpoints ==")
    get_view()
    toggle("binance", "live")
    get_view()
    curl_examples()
