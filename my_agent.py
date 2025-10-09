"""학생 자율주차 알고리즘 클라이언트.

이 스크립트는 시뮬레이터(`demo_self_parking_sim.py`)가 개방한 TCP 포트에
JSONL 프로토콜로 접속한다. 통신 흐름은 아래와 같다.

0. 연결이 성립하면 시뮬레이터가 정적 맵(`{"map": ...}`)을 먼저 보낸다.
1. 이후 시뮬레이터가 매 스텝마다 관측 패킷(`obs`)을 보낸다. 주요 필드:
   - `t`: 시뮬레이터 시간이 초 단위로 증가
   - `state`: 현재 차량 위치(x, y), 각도(yaw), 속도(v)
   - `target_slot`: 목표 주차 슬롯의 직사각형 좌표(xmin, xmax, ymin, ymax)
   - `limits`: 차량 제한(타임스텝, 휠베이스, 조향/가감속 한계 등)
2. 학생 알고리즘은 이 정보를 이용해 다음 명령(`cmd`)을 계산하고,
   `{"steer", "accel", "brake", "gear"}` 값을 JSON 한 줄로 응답한다.
3. 시뮬레이터는 받은 명령을 차량 모델에 적용하고 다음 관측을 보낸다.

학생은 `planner_step()`을 원하는 로직으로 수정해 관측→명령 계산을 구현하면 된다.
시뮬레이터가 아직 실행 중이 아니면 자동으로 재시도하며, 연결이 끊어지면 즉시
다시 접속을 시도한다.
"""

import argparse
import json
import signal
import socket
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PlannerSkeleton:
    """"""

    map_data: Optional[Dict[str, Any]] = None
    waypoints: List[Tuple[float, float]] = None

    def __post_init__(self) -> None:
        if self.waypoints is None:
            self.waypoints = []

    # ------------------------------------------------------------------
    # TODO: 여기에 맵을 활용한 경로 계획/충돌 회피 로직을 구현하세요.
    # ------------------------------------------------------------------
    def set_map(self, map_payload: Dict[str, Any]) -> None:
        """시뮬레이터에서 한 번 보내주는 정적 맵 정보를 저장."""

        self.map_data = map_payload
        self.waypoints.clear()

    def compute_path(self, obs: Dict[str, Any]) -> None:
        """관측값과 맵을 기반으로 목표 슬롯까지의 경로를 생성합니다."""

        # 현재는 구현이 비어 있습니다. ex) A*, RRT, Pure Pursuit 등의 알고리즘을 사용해
        # 중간 웨포인트 생성 등을 여기에 작성할 수 있습니다.
        self.waypoints.clear()

    def compute_control(self, obs: Dict[str, Any]) -> Dict[str, float]:
        """경로를 따라가기 위한 조향/가감속 명령을 산출합니다."""

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
                    continue

                try:
                    cmd = planner_step(packet)
                    payload = json.dumps(cmd, ensure_ascii=False) + "\n"
                    sock.sendall(payload.encode("utf-8"))
                except BrokenPipeError:
                    print("[algo] send failed: broken pipe")
                    return
                except Exception as exc:
                    print(f"[algo] planner/send error: {exc}")

    except (ConnectionResetError, ConnectionAbortedError) as exc:
        print(f"[algo] connection error: {exc}")
    except Exception as exc:
        print(f"[algo] unexpected error while talking to simulator: {exc}")


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
