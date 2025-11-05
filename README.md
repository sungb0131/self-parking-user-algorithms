# Self-Parking User Algorithms Guide

This workspace pairs the `self-parking-sim` simulator with reference student agents. Use the toggles below to read either language.

<details open>
<summary>English</summary>

### 1. Workspace Layout

```
<workspace>/
├── self-parking-sim/              # simulator (TCP server + GUI)
└── self-parking-user-algorithms/  # student planning code (this repo)
```

### 2. Clone the repositories

```bash
cd <workspace>
git clone https://github.com/sungb0131/self-parking-sim.git
git clone https://github.com/sungb0131/self-parking-user-algorithms.git
```

### 3. Prepare a Python environment

This workspace is validated on **Python 3.10** (3.11/3.12 also work). Python 3.13 currently triggers SciPy build failures, so install an interpreter before creating the virtual environment.

```bash
python3 --version
python3.10 --version  # should report 3.10.x once installed
```

Install 3.10 using one of the following options:

- **macOS (Homebrew)**
  ```bash
  brew install python@3.10
  /opt/homebrew/bin/python3.10 --version
  ```
- **Windows**
  - `winget install Python.Python.3.10` or download from [python.org](https://www.python.org/downloads/release/python-3100/)
  - Open a fresh PowerShell and run `python --version` plus `where python` to confirm the path.
- **pyenv**
  ```bash
  pyenv install 3.10.14
  pyenv local 3.10.14
  python --version
  ```

Create the virtual environment inside `self-parking-sim` so both repositories can reuse it.

<details>
<summary>macOS / Linux</summary>

```bash
cd self-parking-sim
/opt/homebrew/bin/python3.10 -m venv .venv  # point to the 3.10 interpreter
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python --version  # expect 3.10.x
```
</details>

<details>
<summary>Windows PowerShell</summary>

```powershell
cd self-parking-sim
C:\Python310\python.exe -m venv .venv  # adjust to your install path
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python --version  # 3.10.x
```
</details>

Reuse the same environment inside this repository:

```bash
# macOS / Linux
source ../self-parking-sim/.venv/bin/activate

# Windows PowerShell
..\self-parking-sim\.venv\Scripts\Activate.ps1
```

### 4. Run the simulator and agent

1. **Start the simulator**
   ```bash
   cd self-parking-sim
   source .venv/bin/activate              # on Windows use .\.venv\Scripts\Activate.ps1
   python demo_self_parking_sim.py
   ```
   Pick a map, then either launch the built-in demo agent or wait for your own client. Using Python older than 3.10 stops at import time, while 3.13 fails during dependency installation—stick to 3.10.x.

2. **Run your algorithm (manual launch)**
   ```bash
   cd self-parking-user-algorithms
   source ../self-parking-sim/.venv/bin/activate
   python my_agent.py --host 127.0.0.1 --port 55556
   ```
   The simulator defaults to `127.0.0.1:55556`. If you change host/port, update both ends.

3. **Replay & logs**
   - Simulator saves to `self-parking-sim/replays/`
   - Student agent saves to `self-parking-user-algorithms/student_replays/`

   Both folders are created on demand and ignored by Git—commit only the JSON sessions you want to share.

### 5. Repository structure

- `my_agent.py` – launcher called by the simulator; usually unchanged.
- `ipc_client.py` – JSONL transport, TCP handling, replay persistence.
- `student_planner.py` – place your planning/control logic; only file students typically modify.

### 6. Map data pipeline (simulator overview)

- `MapAssets`: bundles MATLAB layers (`C`, `Cs`, `Cm`, `Cp`, `slots`, etc.).
- `load_parking_assets`: reads `.mat`, converts to `float32`, and shapes arrays.
- `resize_slots_to_vehicle`, `open_top_parking_lane`, `compute_line_rects`: preprocess geometry to fit the demo vehicle and simplify collisions.
- `build_map_payload`: converts numpy arrays to JSON-friendly types before sending to the client.

### 7. IPC protocol

Messages are exchanged as JSON Lines (one JSON per newline) between the simulator (server) and the student agent (client).

**Flow**
1. On connect the simulator sends a single map packet.
2. Every simulation tick: simulator sends an observation, agent replies with a command.
3. On disconnect the simulator resets and resends a fresh map; the agent should reset internal state.

**Map packet**
```json
{
  "map": {
    "extent": [0.0, 75.0, -25.0, 25.0],
    "cellSize": 0.5,
    "slots": [[10.0, 12.5, -5.0, -1.5], ...],
    "occupied_idx": [0, 1, ...],
    "walls_rects": [[...], ...],
    "lines": [[x1, y1, x2, y2], ...],
    "grid": {
      "stationary": [[...], ...],
      "parked": [[...], ...]
    },
    "expected_orientation": "front_in"
  }
}
```
Agents typically cache this payload for the session.

**Observation packet**
```json
{
  "t": 3.48,
  "state": { "x": 10.15, "y": -4.72, "yaw": 0.78, "v": 1.25 },
  "target_slot": [6.0, 9.2, -3.5, -1.1],
  "limits": {
    "dt": 0.0167,
    "L": 2.6,
    "maxSteer": 0.6109,
    "maxAccel": 3.0,
    "maxBrake": 7.0,
    "steerRate": 3.1416
  }
}
```

**Command packet**
```json
{
  "steer": 0.05,
  "accel": 0.2,
  "brake": 0.0,
  "gear": "D"
}
```
Missing keys default to `0` or `"D"`; the simulator clamps everything before applying it to the motion model.

### 8. Scoring overview

`compute_round_score` in `demo_self_parking_sim.py` calculates the final grade.

- `RoundStats` tracks elapsed time, distance, gear switches, average speed, steering flips, IoU, orientation, and final speed.
- `STAGE_RULES` defines time/distance targets, steering limits, required orientation, and per-metric weights.
- Successful runs start from a fixed safety base (`safe_base = 50`). Normalized metrics (0–1) are multiplied by weights to form the performance component; totals are capped by `score_cap` and reported via `details` for HUD/replays.

### 9. Implementation tips

- Cache the map payload and use the per-tick `obs` to update your planner.
- Respect the limits described in `obs["limits"]` when issuing commands.
- Handle disconnections gracefully—`ipc_client.py` already retries and logs.
- The replay JSON files in `student_replays/` are great for debugging and regression tests.

</details>

<details>
<summary>한국어</summary>

# Self-Parking User Algorithms 사용 가이드

이 저장소는 `self-parking-sim` 시뮬레이터와 IPC(JSON Lines)로 통신하는 학생 알고리즘 예제를 제공합니다. 학생들이 흐름을 이해하고 빠르게 실습을 시작할 수 있도록 설치 절차, 통신 규약, 맵 데이터 파이프라인, 점수 계산 방식을 한 문서로 정리했습니다.

---

## 1. 기본 구성

- **권장 디렉터리 구조**

  ```
  <작업폴더>/
  ├── self-parking-sim/              # 시뮬레이터 (TCP 서버 포함)
  └── self-parking-user-algorithms/  # 학생 알고리즘 (본 저장소)
  ```

- **저장소 클론**

  ```bash
  cd <작업폴더>
  git clone https://github.com/sungb0131/self-parking-sim.git
  git clone https://github.com/sungb0131/self-parking-user-algorithms.git
  ```

- **가상환경 준비**

  이 워크스페이스는 Python 3.10 이상에서 검증되었습니다. **주의: `requirements.txt`로 파이썬 자체를 설치할 수 없으므로**, 먼저 로컬 OS에 3.10 해석기를 설치해 둔 뒤 가상환경을 만드세요. (3.13 이상에서는 SciPy 휠이 없어 빌드 에러가 납니다.)

  ```bash
  python3 --version
  python3.10 --version  # 설치돼 있다면 3.10.x 이상이 출력됩니다.
  ```

  3.10이 없다면 OS별로 아래 방법 중 하나를 사용하세요.

  - **macOS (Homebrew)**  
    ```bash
    brew install python@3.10
    /opt/homebrew/bin/python3.10 --version  # 경로와 버전 확인
    ```
  - **Windows**  
    - `winget install Python.Python.3.10` 또는 [python.org](https://www.python.org/downloads/release/python-3100/) 설치본 사용  
    - 설치 후 새 PowerShell에서 `python --version`과 `where python`으로 위치를 확인합니다.
  - **pyenv 사용자**  
    ```bash
    pyenv install 3.10.14
    pyenv local 3.10.14
    python --version  # pyenv로 선택된 버전 확인
    ```

  <details>
  <summary>macOS / Linux</summary>

  ```bash
  cd self-parking-sim
  # Homebrew 기본 경로 예시: /opt/homebrew/bin/python3.10
  /opt/homebrew/bin/python3.10 -m venv .venv   # 반드시 3.10 이상 해석기를 지정
  source .venv/bin/activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  python --version  # 3.10.x 인지 확인
  ```
  </details>

  <details>
  <summary>Windows PowerShell</summary>

  ```powershell
  cd self-parking-sim
  # python.exe의 경로가 C:\Python310\python.exe 라면 해당 경로를 사용
  C:\Python310\python.exe -m venv .venv   # 설치된 Python이 3.10 이상인지 확인
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  python --version  # 3.10.x
  ```
  </details>

  학생 알고리즘 저장소에서도 같은 가상환경을 재사용합니다.

  ```bash
  # macOS / Linux
  source ../self-parking-sim/.venv/bin/activate

  # Windows PowerShell
  ..\self-parking-sim\.venv\Scripts\Activate.ps1
  ```

---

## 2. 실행 절차

1. **시뮬레이터 실행**

   ```bash
   cd self-parking-sim
   source .venv/bin/activate              # Windows는 .\.venv\Scripts\Activate.ps1
   python demo_self_parking_sim.py
   ```

   홈 화면에서 맵을 선택한 뒤, 우측 패널에서 학생 알고리즘을 실행하거나 수동으로 연결을 대기합니다. Python 3.10 미만에서는 타입 힌트 구문 때문에 실행이 중단되며, 3.13 이상은 의존성 빌드 에러가 발생합니다. 반드시 위 절차대로 3.10 계열 가상환경을 사용하세요.

2. **학생 알고리즘 실행 (수동 실행 시)**

   ```bash
   cd self-parking-user-algorithms
   source ../self-parking-sim/.venv/bin/activate
   python my_agent.py --host 127.0.0.1 --port 55556
   ```

   기본값으로 `host=127.0.0.1`, `port=55556`을 사용합니다. 다른 포트를 사용하려면 시뮬레이터와 학생 알고리즘 모두 동일하게 맞춰야 합니다.

3. **리플레이/로그**

   - 시뮬레이터 로그: `self-parking-sim/replays/`
   - 학생 알고리즘 로그: `self-parking-user-algorithms/student_replays/`

   두 폴더에는 세션별 OBS/CMD 기록이 JSONL로 저장되며, 시뮬레이터 홈 화면에서 리플레이를 바로 재생할 수 있습니다. 리플레이 디렉터리는 실행 시 자동으로 생성되며 Git에는 포함하지 않으니, 필요하다면 원하는 JSON만 골라 별도로 공유하면 됩니다.

---

## 3. 저장소 모듈 구조

학생이 직접 수정해야 하는 코드는 `student_planner.py` 한 파일에 모여 있습니다. `my_agent.py`는 시뮬레이터가 자동으로 호출하는 엔트리포인트로 남겨 두었으며, 내부적으로 통신 모듈(`ipc_client.py`)을 불러와 실행합니다.

- `my_agent.py`: 엔트리포인트. 시뮬레이터 GUI/CLI가 이 파일을 실행하므로 유지해야 합니다. 수정할 필요는 없습니다.
- `ipc_client.py`: TCP 연결, JSONL 송수신, 리플레이 저장 등 네트워크 관련 처리를 담당합니다. 가능한 한 수정하지 않는 것이 좋습니다.
- `student_planner.py`: 맵 수신 처리, 경로 계획, 제어 명령 계산을 위한 스켈레톤이 들어 있습니다. 학생은 이 파일만 자유롭게 수정하면 됩니다.

### 3-1. `student_planner.py` 주요 함수

- `PlannerSkeleton.set_map(map_payload)`  
  시뮬레이터가 연결 직후 보내는 맵 정보를 저장합니다. `extent`, `cellSize`, 슬롯 목록, 정지물 그리드 등을 받아 내부 상태를 초기화합니다. 학생은 필요에 따라 경계값 가공, 슬롯 필터링 등을 추가할 수 있습니다.

- `PlannerSkeleton.compute_path(obs)`  
  관측 데이터(`obs`)와 저장된 맵을 사용해 웨이포인트/경로를 준비하는 자리입니다. 기본 구현은 빈 리스트로 초기화만 하며, 학생이 A*, Hybrid A*, RRT*, 폴리곤 경로 등 원하는 알고리즘을 채워 넣으면 됩니다.

- `PlannerSkeleton.compute_control(obs)`  
  현재 관측값과 준비한 경로를 이용해 `{"steer", "accel", "brake", "gear"}` 명령을 반환합니다. 예시로 간단한 시간 기반 데모 제어가 들어 있으며, 학생은 Pure Pursuit, Stanley 등으로 교체하면 됩니다. 예외가 발생하면 `planner_step`에서 기본 안전 명령(브레이크)을 반환합니다.

- `handle_map_payload(map_payload)`  
  통신 모듈이 맵 패킷을 받았을 때 호출하는 래퍼 함수입니다. 내부적으로 `PlannerSkeleton.set_map`을 호출합니다. 필요 시 맵 로딩 시점에 추가 처리를 하고 싶다면 이 함수에 훅을 넣어도 됩니다.

- `planner_step(obs)`  
  매 틱 호출되며, `compute_control` 결과를 그대로 전달합니다. 예외 처리도 여기서 이뤄집니다. 통신 모듈과의 인터페이스이므로 함수 시그니처는 유지하세요.

이 구조로 학생은 네트워킹에 신경 쓰지 않고, 경로 계획/제어 로직만 구현하면 됩니다.

---

## 4. 맵 데이터 파이프라인

시뮬레이터는 MATLAB `.mat` 파일에서 맵 데이터를 읽어 `MapAssets` 객체로 관리합니다. 주요 단계는 다음과 같습니다.

### 4-1. `MapAssets` 클래스

- 역할: 모든 맵 레이어와 파생 정보를 한 번에 묶어 보관합니다.
- 주요 필드:
  - `C`: 종합 비용맵(디버그용)
  - `Cs`: 정지 물체 레이어(stationary grid)
  - `Cm`: 주차선/노면 마킹 레이어
  - `Cp`: 주차된 차량 레이어
  - `cellSize`: 그리드 해상도(미터)
  - `extent`: 월드 좌표 경계 `[xmin, xmax, ymin, ymax]`
  - `slots`: 주차 슬롯 N×4 배열 `[xmin, xmax, ymin, ymax]`
  - `occupied_idx`: 각 슬롯 점유 여부(bool 배열)
  - `border`, `lines`: 외곽 경계, 차선 세그먼트 정보
  - `walls_rects`: 충돌 판정을 위한 직사각형 모음
  - `FreeThr`, `OccThr`: 그리드 값 해석에 쓰이는 임계값

### 4-2. `load_parking_assets(mat_path)`

1. MATLAB `.mat` 파일을 읽어 numpy 배열로 변환합니다.
2. double 자료형은 `float32`로 다운캐스팅하여 메모리 사용량을 줄입니다.
3. 스칼라 값은 `squeeze()` 후 파이썬 float/tuple로 변환합니다.
4. 슬롯, 차선, 충돌 박스 등은 그대로 numpy 배열로 유지합니다.
5. 반환값은 `MapAssets` 인스턴스입니다.

### 4-3. 맵 변형 & 전처리

- `resize_slots_to_vehicle(M)`: 차량 크기와 마진에 맞춰 슬롯 폭·길이를 보정합니다. 슬롯 중심은 유지하고 좌우/전후 마진만 조정합니다.
- `open_top_parking_lane(M)`: 맵 상단 진입 경계선을 제거하여 학생 차량이 쉽게 진입할 수 있도록 합니다.
- `compute_line_rects(M)`: 차선 세그먼트를 얇은 직사각형으로 변환하여 충돌 판정용 데이터(`walls_rects`)를 보강합니다.
- `ensure_map_loaded(map_cfg, cache, seed)`: 위 전처리를 순차 실행한 뒤,
  1. 비어 있는 슬롯 중 하나를 타깃 슬롯으로 선택합니다.
  2. 학생에게 보내줄 JSON payload를 미리 구성합니다.
  3. 썸네일 등 메타 정보를 만들어 캐시에 저장합니다.

### 4-4. `build_map_payload(M)`

학생에게 전송할 수 있도록 numpy 배열을 표준 파이썬 리스트/스칼라로 변환합니다. 반환 구조는 다음과 같습니다.

```json
{
  "extent": [xmin, xmax, ymin, ymax],
  "cellSize": 0.1,
  "slots": [[xmin, xmax, ymin, ymax], ...],
  "occupied_idx": [0, 1, ...],
  "walls_rects": [[...], ...],
  "lines": [[x1, y1, x2, y2], ...],
  "grid": {
    "stationary": [[...], ...],
    "parked": [[...], ...]
  },
  "expected_orientation": "front_in"
}
```

학생 알고리즘은 이 payload를 그대로 저장하거나 필요한 레이어만 선별해 사용하면 됩니다.

---

## 5. IPC 통신 규약

모든 메시지는 **JSON Lines** 형식(한 줄에 하나의 JSON, 줄바꿈으로 구분)으로 송신합니다. 연결은 단일 TCP 클라이언트(학생 알고리즘)와 서버(시뮬레이터) 구조입니다.

### 5-1. 메시지 흐름

1. **연결 직후**: 시뮬레이터가 맵 패킷을 한 번 전송합니다.
2. **매 시뮬레이션 틱**: 시뮬레이터가 관측(obs) 패킷을 보내고, 학생 알고리즘은 명령(cmd) 패킷으로 응답합니다.
3. **끊김 처리**: 네트워크 오류가 발생하면 시뮬레이터가 연결을 초기화하고 새 맵을 재전송합니다. 학생 측에서는 연결 종료를 감지하고 상태를 리셋해야 합니다.

### 5-2. 맵 패킷 (`{"map": {...}}`)

```json
{
  "map": {
    "extent": [0.0, 75.0, -25.0, 25.0],
    "cellSize": 0.5,
    "slots": [[10.0, 12.5, -5.0, -1.5], ...],
    "occupied_idx": [0, 1, ...],
    "walls_rects": [[...], ...],
    "lines": [[x1, y1, x2, y2], ...],
    "grid": {
      "stationary": [[...], ...],
      "parked": [[...], ...]
    },
    "expected_orientation": "front_in"
  }
}
```

학생 알고리즘은 맵을 한 번만 받아 캐시한 뒤 세션 동안 재사용합니다.

### 5-3. 관측 패킷 (`obs`)

```json
{
  "t": 3.4833,
  "state": { "x": 10.15, "y": -4.72, "yaw": 0.78, "v": 1.25 },
  "target_slot": [6.0, 9.2, -3.5, -1.1],
  "limits": {
    "dt": 0.0167,
    "L": 2.6,
    "maxSteer": 0.6109,
    "maxAccel": 3.0,
    "maxBrake": 7.0,
    "steerRate": 3.1416
  }
}
```

- `t`: 경과 시간(초)
- `state`: 차량 위치, 헤딩, 속도
- `target_slot`: 주차 목표 슬롯 경계
- `limits`: 차량 모델에서 허용하는 제약치(시간 간격, 조향 한계, 가감속 한계 등)

### 5-4. 명령 패킷 (`cmd`)

```json
{
  "steer": 0.05,   // 라디안 단위 조향 목표
  "accel": 0.2,    // 0~1 스로틀
  "brake": 0.0,    // 0~1 브레이크
  "gear": "D"      // "D" 또는 "R"
}
```

필수 키가 누락되면 시뮬레이터가 `0` 또는 `"D"`로 보정합니다. 시뮬레이터는 수신된 값을 clamp한 뒤 차량 모델에 적용합니다.

---

## 6. 점수 산정 로직

평가 흐름은 `demo_self_parking_sim.py` 내부 `compute_round_score`를 기준으로 합니다.

### 6-1. `RoundStats` 구조

주행 중 매 틱마다 누적되는 통계입니다.

- `elapsed`: 총 주행 시간(초)
- `distance`: 이동 거리(미터)
- `gear_switches`: 기어 전환 횟수
- `avg_speed_accum`, `speed_samples`: 평균 속도 산출용 누적 값
- `direction_flips`: 전진↔후진 전환 횟수
- `final_iou`: 종료 시 차량과 슬롯의 IoU
- `final_orientation`: 종료 시 주차 방향 (`front_in`, `rear_in`, `unknown`)
- `final_speed`: 마지막 속도(정차 여부 판단)

### 6-2. `STAGE_RULES`

맵 구성별로 목표 시간, 이동 거리, 조향 변화 한계, 속도 목표, 주차 방향 요구 사항을 정의합니다. 항목별 가중치(`weights`)를 합산하여 패널티를 계산합니다.

### 6-3. `compute_round_score`

1. 라운드 결과가 실패(`reason != "success"`)일 경우 0점을 반환합니다.
2. 스테이지 설정에서 목표 값을 불러오고, 맵 대각선 길이를 기반으로 이동 거리 목표를 계산합니다.
3. 시간, 거리, 기어 전환, 평균 속도, 조향 변경 수, 주차 IoU, 주차 방향, 최종 정차 여부를 각각 0~1 범위로 정규화합니다.
4. 정규화된 점수에 가중치를 곱해 `performance_component`를 계산합니다.
5. `safe_base`(안전 점수)에 성능 점수를 더해 최종 점수를 산출하고, 상한선(`score_cap`)을 적용합니다.
6. 세부 항목 점수와 총합은 `details["component_scores"]`에 저장되어 HUD와 리플레이 요약에 활용됩니다.

---

## 7. 학생 알고리즘 구현 팁

- 맵 payload를 수신하면 경계와 슬롯 정보를 캐시해 두고, 관측 패킷만으로 알고리즘을 수행합니다.
- 관측 패킷의 `limits`를 기반으로 제약 조건(조향 속도, 가감속)을 반드시 준수합니다.
- 연결이 끊기면 소켓 예외를 감지하고 재접속 루틴을 준비합니다.
- `student_replays/`에 저장되는 리플레이(JSONL)를 사용하면 디버깅과 리그레이션 테스트가 용이합니다.

---

</details>

