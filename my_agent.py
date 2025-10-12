"""학생 자율주차 알고리즘 클라이언트.

시뮬레이터(`demo_self_parking_sim.py`)와의 통신은 JSON Lines(JSONL) 형식의
TCP 스트림으로 이루어진다. 한 세션에서 오가는 메시지 구조는 다음과 같다.

1. **맵 페이로드** — 연결 직후 시뮬레이터가 한 번 전송
   ```json
   {"map": {
       "extent": [xmin, xmax, ymin, ymax],
       "cellSize": 0.2,
       "slots": [[xmin, xmax, ymin, ymax], ...],
       "occupied_idx": [0, 1, ...],
       "walls_rects": [...],
       "lines": [...],
       "grid": {
           "stationary": [...],
           "parked": [...]
       }
   }}
   ```
   → 학생 측은 `set_map()`에서 이 정보를 저장해 경로 계획에 활용하면 된다.

2. **관측 패킷(obs)** — 매 시뮬레이션 스텝마다 전송
   ```json
   {
       "t": 3.48,
       "state": {"x": ..., "y": ..., "yaw": ..., "v": ...},
       "target_slot": [xmin, xmax, ymin, ymax],
       "limits": {
           "dt": 0.0167, "L": 2.6,
           "maxSteer": 0.61, "maxAccel": 3.0,
           "maxBrake": 7.0, "steerRate": 3.14
       }
   }
   ```

3. **명령 패킷(cmd)** — 학생 알고리즘이 각 스텝마다 응답
   ```json
   {"steer": 0.05, "accel": 0.2, "brake": 0.0, "gear": "D"}
   ```

본 파일은 최소한의 스켈레톤을 제공한다. `planner_step`을 수정해 원하는
경로 계획·제어 로직을 구현하면 되고, 기본 구현은 간단한 데모 동작만 수행한다.
"""

import argparse
import json
import os
import signal
import socket
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def pretty_print_map_summary(map_payload: Dict[str, Any]) -> None:
    extent = map_payload.get("extent") or [None, None, None, None]
    slots = map_payload.get("slots") or []
    occupied = map_payload.get("occupied_idx") or []
    free_slots = len(slots) - sum(1 for v in occupied if v)
    print("[algo] map extent :", extent)
    print("[algo] total slots:", len(slots), "/ free:", free_slots)
    stationary = map_payload.get("grid", {}).get("stationary")
    if stationary:
        rows = len(stationary)
        cols = len(stationary[0]) if rows and len(stationary[0]) else 0
        print("[algo] grid size  :", rows, "x", cols)


@dataclass
class PlannerSkeleton:
    """간단한 레퍼런스 구현.

    - `set_map`에서 맵 정보를 저장하고 간단한 통계를 출력한다.
    - `compute_path`/`compute_control` 자리에 사용자가 원하는 로직을 채워 넣으면 된다.
    """

    map_data: Optional[Dict[str, Any]] = None
    map_extent: Optional[Tuple[float, float, float, float]] = None
    cell_size: float = 0.5
    stationary_grid: Optional[List[List[float]]] = None
    waypoints: List[Tuple[float, float]] = None
    last_target_slot: Optional[Tuple[float, float, float, float]] = None

    def __post_init__(self) -> None:
        if self.waypoints is None:
            self.waypoints = []

    def set_map(self, map_payload: Dict[str, Any]) -> None:
        """시뮬레이터에서 전송한 정적 맵 데이터를 보관."""

        self.map_data = map_payload
        self.map_extent = tuple(map(float, map_payload.get("extent", (0.0, 0.0, 0.0, 0.0))))
        self.cell_size = float(map_payload.get("cellSize", 0.5))
        self.stationary_grid = map_payload.get("grid", {}).get("stationary")
        pretty_print_map_summary(map_payload)
        self.waypoints.clear()
        self.last_target_slot = None

    def compute_path(self, obs: Dict[str, Any]) -> None:
        """관측과 맵을 이용해 경로를 준비한다. (현재는 예제용으로 비워 둠)"""

        # TODO: A*, RRT*, Hybrid A* 등으로 self.waypoints를 채우세요.
        self.waypoints.clear()

    def compute_control(self, obs: Dict[str, Any]) -> Dict[str, float]:
        """경로를 따라가기 위한 조향/가감속 명령을 산출합니다."""

        # 목표 슬롯이 바뀌었는지 감지해 경로를 갱신한다.
        target_slot = obs.get("target_slot")
        if target_slot is not None:
            target_tuple = tuple(float(v) for v in target_slot)
        else:
            target_tuple = None
        if target_tuple and target_tuple != self.last_target_slot:
            self.compute_path(obs)
            self.last_target_slot = target_tuple

        # 예시: 기본 데모 로직 (시간 기반 제어). 학생들은 여기를 대체해
        # Pure Pursuit, Stanley, MPC 등 원하는 로직을 넣을 수 있습니다.
        t = float(obs.get("t", 0.0))
        v = float(obs.get("state", {}).get("v", 0.0))

        cmd = {"steer": 0.0, "accel": 0.0, "brake": 0.0, "gear": "D"}

        if t < 2.0:
            cmd["accel"] = 0.6
        elif t < 3.0:
            cmd["brake"] = 0.3
        else:
            cmd["steer"] = 0.07
            if v < 1.0:
                cmd["accel"] = 0.2

        return cmd


planner = PlannerSkeleton()

STUDENT_REPLAY_DIR = "student_replays"

def _slugify(text: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(text))
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


def planner_step(obs: Dict[str, Any]) -> Dict[str, Any]:

    try:
        return planner.compute_control(obs)
    except Exception as exc:
        print(f"[algo] planner_step error: {exc}")
        return {"steer": 0.0, "accel": 0.0, "brake": 0.5, "gear": "D"}


def run_session(sock: socket.socket, peer: Tuple[str, int]) -> None:
    """시뮬레이터와의 단일 TCP 세션을 처리."""

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
                    planner.set_map(packet["map"])
                    print("[algo] received static map payload")
                    map_payload = packet["map"]
                    session_meta["map_key"] = map_payload.get("key") or map_payload.get("name")
                    session_meta["map_name"] = map_payload.get("name") or map_payload.get("key")
                    session_meta["map_extent"] = map_payload.get("extent")
                    session_meta["slots_total"] = len(map_payload.get("slots", []))
                    continue

                try:
                    cmd = planner_step(packet)
                    payload = json.dumps(cmd, ensure_ascii=False) + "\n"
                    sock.sendall(payload.encode("utf-8"))
                    frames.append({
                        "t": packet.get("t"),
                        "obs": packet,
                        "cmd": cmd,
                    })
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
    """시뮬레이터가 열어둔 포트에 접속해 세션을 유지한다."""

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=55556)
    options = parser.parse_args()

    # Ctrl+C 입력 시 즉시 종료
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    run_client(options.host, options.port)


if __name__ == "__main__":
    main()
