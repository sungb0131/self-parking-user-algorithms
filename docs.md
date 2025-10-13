# self-parking-sim

Self-Parking 시뮬레이터와 학생 알고리즘 레포를 함께 받아서 실행하는 방법 정리

## 1. 디렉터리 구조

두 저장소를 같은 상위 폴더에 나란히 두는 것을 권장합니다.

```
<작업폴더>/
├── self-parking-sim/              # 시뮬레이터 (본 저장소)
└── self-parking-user-algorithms/  # 학생 알고리즘 예제
```

## 2. 저장소 클론

```bash
cd <작업폴더>
git clone https://github.com/sungb0131/self-parking-sim.git
git clone https://github.com/sungb0131/self-parking-user-algorithms.git
```

## 3. 가상환경 생성 및 의존성 설치

시뮬레이터 레포 안에 가상환경을 만들어 사용합니다.

```bash
cd self-parking-sim
python3 -m venv .venv           # 가상환경 생성
source .venv/bin/activate       # macOS/Linux
# Windows PowerShell: .venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt
```

학생 알고리즘 레포에서도 같은 가상환경을 재사용하면 됩니다. (예: `source ../self-parking-sim/.venv/bin/activate`)

## 4. 시뮬레이터 실행

```bash
cd self-parking-sim
source .venv/bin/activate
python demo_self_parking_sim.py --mode ipc
```

실행하면 홈 화면(맵 선택)이 나타나고, 우측 패널에서 학생 알고리즘을 바로 실행하거나 리플레이를 재생할 수 있습니다.

## 5. 학생 알고리즘 실행 (선택 사항)

별도 터미널에서 직접 실행하고 싶다면:

```bash
cd self-parking-user-algorithms
source ../self-parking-sim/.venv/bin/activate
python my_agent.py --host 127.0.0.1 --port 55556
```

홈 화면에서 자동으로 실행할 수 있으므로 수동 실행은 선택 사항입니다.

## 6. 리플레이 및 로그

- 시뮬레이터: `self-parking-sim/replays/`
- 학생 알고리즘: `self-parking-user-algorithms/student_replays/`

각 폴더에 JSON 리플레이가 저장되며, 홈 화면 우측 패널에서 바로 불러올 수 있습니다.






1. 세션 시작 직후
시뮬레이터는 TCP 연결이 열리자마자 정적 맵 패킷을 한 번 보냅니다.

{ "map": { ... } }
맵 페이로드 구성요소:

extent [xmin, xmax, ymin, ymax] : 월드 좌표 경계
cellSize : 격자 해상도 (m)
slots : 주차 슬롯 목록 [[xmin, xmax, ymin, ymax], …]
occupied_idx : 각 슬롯이 점유되었는지(1)/비었는지(0)
walls_rects, lines : 장애물/차선 등의 선형 정보
grid.stationary, grid.parked : 셀 단위 정지물/주차 차량 레이어(0~1 값)
학생 코드는 이 맵을 파싱해 내부 환경 정보를 캐싱하면 됩니다.
2. 매 시뮬레이션 스텝 (OBS 패킷)
맵 전송 이후 시뮬레이터는 한 스텝마다 다음 구조의 관측 패킷을 보냅니다.

{
  "t": 3.4833,
  "state": {
    "x": 10.15,
    "y": -4.72,
    "yaw": 0.78,
    "v": 1.25
  },
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
필드 설명:

t : 시뮬레이터 경과 시간(초)
state : 현재 차량 상태 (좌표, 헤딩, 속도)
target_slot : 목표 슬롯의 좌표 범위
limits : 알고리즘이 지켜야 할 차량 제약 (조향 한계, 가감속 한계 등)
이 obs 딕셔너리를 받아 planner_step(obs)에서 원하는 알고리즘 로직을 수행하면 됩니다.

3. 명령 응답 (CMD 패킷)
학생 알고리즘은 각 스텝마다 OBS를 받은 뒤 아래 형식으로 응답합니다.

{
  "steer": 0.05,        # radians (조향 목표값)
  "accel": 0.2,         # 0~1 (비례 스로틀)
  "brake": 0.0,         # 0~1 (비례 브레이크)
  "gear": "D"           # or "R"
}
값이 누락되면 기본값(0 또는 D)으로 처리되며, 시뮬레이터에서 clamp 후 차량 모델에 적용합니다.

4. 예외·리플레이
전송 중 오류가 나면 시뮬레이터가 연결을 재설정하고 맵을 다시 보낸 뒤 관측을 재개하므로 학생 측도 재연결·초기화를 감지해야 합니다.
모든 OBS/CMD는 시뮬레이터 replays/와 학생 student_replays/에 JSON으로 저장되므로 디버깅·복기에 활용할 수 있습니다.
