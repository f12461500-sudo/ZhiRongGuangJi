"""物理常量和默认仿真参数"""

# === 材料属性库 ===
MATERIALS = {
    "Ti-6Al-4V (TC4钛合金)": {
        "name": "Ti-6Al-4V",
        "density": 4430.0,            # kg/m³
        "specific_heat": 560.0,       # J/(kg·K)
        "thermal_conductivity": 7.0,  # W/(m·K)
        "absorptivity": 0.40,         # 激光吸收率
        "melting_temp": 1660.0,       # °C 熔点
    },
    "Inconel 718 (镍基高温合金)": {
        "name": "Inconel 718",
        "density": 8190.0,
        "specific_heat": 435.0,
        "thermal_conductivity": 11.4,
        "absorptivity": 0.35,
        "melting_temp": 1336.0,
    },
    "Al2O3 陶瓷基复合材料": {
        "name": "Al2O3 Ceramic",
        "density": 3950.0,
        "specific_heat": 880.0,
        "thermal_conductivity": 2.5,
        "absorptivity": 0.55,
        "melting_temp": 2072.0,
    },
}

# === 激光默认参数 ===
DEFAULT_LASER = {
    "power": 400.0,          # 激光功率 (W)
    "beam_radius": 1.5e-3,   # 光斑半径 (m)
    "scan_width": 8.0e-3,    # 扫描宽度 (m)
    "feed_rate": 8.0e-3,     # 进给速度 (m/s)
}

# === 网格默认参数 (25mm x 15mm x 3mm 工件) ===
DEFAULT_GRID = {
    "nx": 50,                # X: 50*0.5mm = 25mm
    "ny": 30,                # Y: 30*0.5mm = 15mm
    "nz": 8,                 # Z: 8*0.375mm = 3mm
    "dx": 0.5e-3,
    "dy": 0.5e-3,
    "dz": 0.375e-3,
}

# === 时间步参数 ===
DEFAULT_TIME = {
    "total_time": 2.0,       # 总仿真时间 (s)
    "dt": 0.001,             # 时间步长 (s)
    "snapshot_interval": 40, # 每N步记录快照
}

# === 环境/边界条件 ===
AMBIENT_TEMP = 25.0          # 环境/初始温度 (°C)
CONVECTION_COEFF = 10.0      # 自然对流系数 W/(m²·K)

# === 轨迹类型 ===
TRAJECTORY_TYPES = ["直线", "正弦曲线", "S形曲线"]
