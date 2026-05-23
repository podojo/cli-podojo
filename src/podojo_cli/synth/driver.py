"""Playwright driver subprocess for synthetic usertests.

Reads commands from <session>/cmd.json, executes them against a browser, and
writes state to <session>/state.json plus screenshots to <session>/shots/.

Run via: python -m podojo_cli.synth.driver --url <preview-url> --session-dir <dir>
"""
import argparse
import json
import os
import time
import traceback
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="usertest preview URL")
    ap.add_argument("--session-dir", required=True, help="session working directory")
    ap.add_argument("--headed", action="store_true", help="show browser window")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _write_error(
            args.session_dir,
            "playwright is not installed. Install with: pip install 'podojo-cli[synth]' "
            "&& playwright install chromium",
        )
        return

    session_dir = Path(args.session_dir)
    shots_dir = session_dir / "shots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    cmd_path = session_dir / "cmd.json"
    state_path = session_dir / "state.json"
    user_data_dir = session_dir / "userdata"

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=not args.headed,
            permissions=["microphone", "camera"],
            viewport={"width": 1400, "height": 900},
            args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        def dump(idx: int, note: str = "", last_cmd: dict | None = None) -> None:
            shot = str(shots_dir / f"shot_{idx:03d}.png")
            try:
                page.screenshot(path=shot, full_page=True)
            except Exception as e:
                shot = f"screenshot_err: {e}"
            try:
                text = page.inner_text("body")[:8000]
            except Exception as e:
                text = f"text_err: {e}"
            buttons = _safe_collect(page, "button")
            links = _safe_collect_links(page)
            inputs = _safe_collect_inputs(page)
            iframes = [
                {"url": f.url, "name": f.name}
                for f in page.frames
                if f != page.main_frame
            ]
            state = {
                "idx": idx,
                "note": note,
                "url": page.url,
                "title": _safe(lambda: page.title(), ""),
                "screenshot": shot,
                "text": text,
                "buttons": buttons,
                "links": links,
                "inputs": inputs,
                "iframes": iframes,
                "last_cmd": last_cmd,
            }
            state_path.write_text(json.dumps(state, indent=2))

        try:
            page.goto(args.url, wait_until="domcontentloaded")
        except Exception as e:
            _write_error(args.session_dir, f"failed to load {args.url}: {e}")
            ctx.close()
            return
        time.sleep(3)
        dump(0, "initial load")

        idx = 1
        while True:
            time.sleep(0.5)
            if not cmd_path.exists():
                continue
            try:
                cmd = json.loads(cmd_path.read_text())
            except Exception:
                continue
            cmd_path.unlink(missing_ok=True)
            note = cmd.get("note", json.dumps(cmd)[:120])
            try:
                _execute(page, cmd)
                if cmd.get("op") == "quit":
                    break
                time.sleep(cmd.get("wait_after", 2))
                dump(idx, note, cmd)
            except Exception as e:
                err = {
                    "idx": idx,
                    "note": note,
                    "error": str(e),
                    "trace": traceback.format_exc(),
                    "last_cmd": cmd,
                }
                state_path.write_text(json.dumps(err, indent=2))
            idx += 1

        ctx.close()


def _execute(page, cmd: dict) -> None:
    op = cmd.get("op")
    if op == "quit":
        return
    if op == "click_text":
        page.get_by_text(cmd["text"], exact=cmd.get("exact", False)).first.click()
    elif op == "click_role":
        page.get_by_role(
            cmd["role"], name=cmd["name"], exact=cmd.get("exact", False)
        ).first.click()
    elif op == "click_selector":
        page.click(cmd["selector"])
    elif op == "click_xy":
        page.mouse.click(cmd["x"], cmd["y"])
    elif op == "swipe_xy":
        steps = cmd.get("steps", 20)
        page.mouse.move(cmd["x1"], cmd["y1"])
        page.mouse.down()
        page.mouse.move(cmd["x2"], cmd["y2"], steps=steps)
        page.mouse.up()
    elif op == "fill":
        page.fill(cmd["selector"], cmd["value"])
    elif op == "fill_role":
        page.get_by_role(cmd["role"], name=cmd["name"]).fill(cmd["value"])
    elif op == "press":
        page.keyboard.press(cmd["key"])
    elif op == "type":
        page.keyboard.type(cmd["text"])
    elif op == "wait":
        time.sleep(cmd.get("seconds", 2))
    elif op == "screenshot":
        pass
    elif op == "reload":
        page.reload()
    elif op == "goto":
        page.goto(cmd["url"])
    elif op == "iframe_click":
        f = page.frame_locator(cmd.get("iframe_selector", "iframe"))
        f.get_by_text(cmd["text"], exact=cmd.get("exact", False)).first.click()
    elif op == "iframe_click_css":
        f = page.frame_locator(cmd.get("iframe_selector", "iframe"))
        f.locator(cmd["css"]).first.click()
    elif op == "frame_click_xy":
        target = next((f for f in page.frames if f != page.main_frame), None)
        if target is None:
            raise RuntimeError("no prototype iframe found")
        box = target.frame_element().bounding_box()
        if box is None:
            raise RuntimeError("prototype iframe has no bounding box")
        page.mouse.click(box["x"] + cmd["x"], box["y"] + cmd["y"])
    elif op == "frame_swipe_xy":
        target = next((f for f in page.frames if f != page.main_frame), None)
        if target is None:
            raise RuntimeError("no prototype iframe found")
        box = target.frame_element().bounding_box()
        if box is None:
            raise RuntimeError("prototype iframe has no bounding box")
        steps = cmd.get("steps", 20)
        x1, y1 = box["x"] + cmd["x1"], box["y"] + cmd["y1"]
        x2, y2 = box["x"] + cmd["x2"], box["y"] + cmd["y2"]
        page.mouse.move(x1, y1)
        page.mouse.down()
        page.mouse.move(x2, y2, steps=steps)
        page.mouse.up()
    elif op == "advance":
        for _ in range(cmd.get("times", 1)):
            clicked = False
            for label in ("Done with Step", "Continue"):
                try:
                    page.get_by_role(
                        "button", name=label, exact=True
                    ).first.click(timeout=3000)
                    clicked = True
                    break
                except Exception:
                    continue
            if not clicked:
                break
            time.sleep(1.5)
    else:
        raise ValueError(f"unknown op {op!r}")


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def _safe_collect(page, selector: str) -> list[str]:
    out: list[str] = []
    try:
        for el in page.query_selector_all(selector):
            try:
                t = el.inner_text().strip()
                if t:
                    out.append(t)
            except Exception:
                pass
    except Exception:
        pass
    return out


def _safe_collect_links(page) -> list[dict]:
    out: list[dict] = []
    try:
        for a in page.query_selector_all("a"):
            try:
                t = a.inner_text().strip()
                if t:
                    out.append({"text": t, "href": a.get_attribute("href")})
            except Exception:
                pass
    except Exception:
        pass
    return out


def _safe_collect_inputs(page) -> list[dict]:
    out: list[dict] = []
    try:
        for i in page.query_selector_all("input, textarea, select"):
            try:
                out.append(
                    {
                        "type": i.get_attribute("type"),
                        "placeholder": i.get_attribute("placeholder"),
                        "name": i.get_attribute("name"),
                        "value": i.get_attribute("value"),
                    }
                )
            except Exception:
                pass
    except Exception:
        pass
    return out


def _write_error(session_dir: str, message: str) -> None:
    state_path = Path(session_dir) / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"idx": 0, "error": message}, indent=2))


if __name__ == "__main__":
    main()
