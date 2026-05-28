"""预设Demo场景 - 典型应用案例"""

DEMO_SCENARIOS = {
    "航空发动机涡轮叶片 (TC4直线路径)": {
        "description": "模拟航空发动机涡轮叶片的直线铣削加工，钛合金TC4材料。"
                       "传统扫描产生明显哑铃型温度场，优化后实现均匀加热。",
        "material_name": "Ti-6Al-4V (TC4钛合金)",
        "path_type": "直线",
        "laser_power": 400.0,
        "beam_radius": 1.0e-3,
        "scan_width": 10.0e-3,
        "feed_rate": 10.0e-3,
    },
    "飞机起落架曲面加工 (Inconel 718 S形路径)": {
        "description": "模拟飞机起落架复杂曲面加工，Inconel 718高温合金。"
                       "S形铣削路径含大曲率转弯，动态角度因子在此场景效果显著。",
        "material_name": "Inconel 718 (镍基高温合金)",
        "path_type": "S形曲线",
        "laser_power": 500.0,
        "beam_radius": 1.2e-3,
        "scan_width": 12.0e-3,
        "feed_rate": 8.0e-3,
    },
    "陶瓷基复合材料加工 (Al2O3 正弦路径)": {
        "description": "模拟陶瓷基复合材料波浪形铣削加工。Al2O3导热性极低，"
                       "热量高度集中，对轨迹优化的依赖度最高。",
        "material_name": "Al2O3 陶瓷基复合材料",
        "path_type": "正弦曲线",
        "laser_power": 300.0,
        "beam_radius": 0.8e-3,
        "scan_width": 8.0e-3,
        "feed_rate": 12.0e-3,
    },
    "航天结构件精密加工 (TC4 宽幅扫描)": {
        "description": "模拟宽幅激光扫描场景，扫描宽度达14mm。"
                       "传统方法在宽幅下不均匀性更加严重，优化效果尤为突出。",
        "material_name": "Ti-6Al-4V (TC4钛合金)",
        "path_type": "直线",
        "laser_power": 500.0,
        "beam_radius": 0.8e-3,
        "scan_width": 14.0e-3,
        "feed_rate": 8.0e-3,
    },
}


def get_demo_list():
    """返回Demo场景名称列表"""
    return list(DEMO_SCENARIOS.keys())


def get_demo_params(scenario_name):
    """获取指定场景的参数"""
    return DEMO_SCENARIOS.get(scenario_name)
