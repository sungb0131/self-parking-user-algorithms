"""시뮬레이터와 통신을 담당하는 모듈.

이 파일은 가능한 한 수정하지 않고, 알고리즘 변경은 `student_planner.py`
내 `PlannerSkeleton` 및 `planner_step` 구현만 손보면 됩니다.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from student_planner import handle_map_payload, planner_step  # 학생 구현 모듈


STUDENT_REPLAY_DIR = "student_replays"


def _slugify(text: Any) -> str:
    slug = "".join(ch.lower() if str(ch).isalnum() else "_" for ch in str(text))
    slug = slug.strip("_")
    return slug or "session"


def save_student_replay(frames: List[Dict[str, Any]], meta: Dict[str, Any]) -> Optional[str]:
    if not frames:
        return None
    try:
        os.makedirs(STUDENT_REPLAY_DIR, exist_ok=True)
    except Exception as exc:
        print(f"[algo] replay dir error: {exc}")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    map_key = meta.get("map_key") or meta.get("map_name") or "session"
    filename = f"{timestamp}_{_slugify(map_key)}.json"
    path = os.path.join(STUDENT_REPLAY_DIR, filename)
    payload = {
        "meta": meta,
        "frames": frames,
    }
    try:
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)
        print(f"[algo] replay saved: {path}")
        return path
    except Exception as exc:
        print(f"[algo] replay save failed: {exc}")
        return None


def run_session(sock: socket.socket, peer: Tuple[str, int]) -> None:
    """시뮬레이터와의 단일 TCP 세션을 처리합니다."""

    print(f"[algo] connected to simulator at {peer}")
    buffer = b""
    frames: List[Dict[str, Any]] = []
    session_meta: Dict[str, Any] = {
        "peer": {"host": peer[0], "port": peer[1]},
        "start_time": datetime.now().isoformat(timespec="seconds"),
        "map_key": None,
        "map_name": None,
    }

    try:
        while True:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                print("[algo] simulator closed the connection")
                break

            buffer += chunk

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line.strip():
                    continue

                try:
                    packet = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    print(f"[algo] bad JSON from simulator: {exc}")
                    continue

                if isinstance(packet, dict) and "map" in packet:
                    map_payload = packet["map"]
                    handle_map_payload(map_payload)
                    print("[algo] received static map payload")
                    session_meta["map_key"] = map_payload.get("key")
                    session_meta["map_name"] = map_payload.get("name")
                    session_meta["map_extent"] = map_payload.get("extent")
                    session_meta["slots_total"] = len(map_payload.get("slots", []))
                    continue

                try:
                    cmd = planner_step(packet)
                    payload = json.dumps(cmd, ensure_ascii=False) + "\n"
                    sock.sendall(payload.encode("utf-8"))
                    frames.append(
                        {
                            "t": packet.get("t"),
                            "obs": packet,
                            "cmd": cmd,
                        }
                    )
                except BrokenPipeError:
                    print("[algo] send failed: broken pipe")
                    return
                except Exception as exc:
                    print(f"[algo] planner/send error: {exc}")

    except (ConnectionResetError, ConnectionAbortedError) as exc:
        print(f"[algo] connection error: {exc}")
    except Exception as exc:
        print(f"[algo] unexpected error while talking to simulator: {exc}")
    finally:
        session_meta["end_time"] = datetime.now().isoformat(timespec="seconds")
        session_meta["frame_count"] = len(frames)
        save_student_replay(frames, session_meta)


def run_client(host: str, port: int) -> None:
    """시뮬레이터가 열어둔 포트에 접속해 세션을 유지합니다."""

    backoff = 1.0
    while True:
        try:
            print(f"[algo] connecting to simulator at {host}:{port} ...")
            with socket.create_connection((host, port), timeout=2.0) as sock:
                sock.settimeout(0.2)
                run_session(sock, sock.getpeername())
                backoff = 1.0  # 연결이 정상 종료되면 지연을 초기화
        except KeyboardInterrupt:
            print("\n[algo] stopping by keyboard interrupt")
            break
        except (ConnectionRefusedError, TimeoutError, OSError) as exc:
            print(f"[algo] connect failed ({exc}); retrying in {backoff:.1f}s")
            time.sleep(backoff)
            backoff = min(backoff + 0.5, 5.0)
            continue

        # 시뮬레이터가 연결을 닫은 경우 짧게 대기 후 재시도
        print("[algo] lost connection - waiting 1.0s before retry")
        time.sleep(1.0)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=55556)
    options = parser.parse_args(argv)

    # Ctrl+C 입력 시 즉시 종료
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    run_client(options.host, options.port)


if __name__ == "__main__":
    main()
