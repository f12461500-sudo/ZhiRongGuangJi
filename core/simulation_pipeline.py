"""仿真管线 - 串联轨迹生成、功率优化、热传导仿真

对比策略:
- 优化前: 传统正弦振荡 + 恒定功率 -> 哑铃型温度场
- 优化后: 传统正弦振荡 + 密度补偿功率 -> 均匀温度场 (香肠型)
"""

import numpy as np
from core.config import MATERIALS, DEFAULT_GRID, AMBIENT_TEMP
from core.trajectory import TrajectoryGenerator
from core.power_optimizer import PowerOptimizer
from core.thermal_model import ThermalSimulator


def run_comparison_simulation(material_name, path_type, laser_power, beam_radius,
                               scan_width, feed_rate, grid_config=None):
    """运行完整对比仿真

    Returns dict with before/after results for visualization.
    """
    material = MATERIALS.get(material_name, MATERIALS["Ti-6Al-4V (TC4钛合金)"])
    grid = grid_config or DEFAULT_GRID
    grid_w = (grid["nx"] - 1) * grid["dx"]
    grid_h = (grid["ny"] - 1) * grid["dy"]

    total_length = grid_w * 0.80
    path_y_center = grid_h / 2

    # === 生成轨迹 ===
    # 优化前: 传统正弦振荡 (时间均匀采样 -> 点密度不均)
    traj_gen_before = TrajectoryGenerator(
        scan_width=scan_width, feed_rate=feed_rate, n_oscillation_cycles=15)
    result_before = traj_gen_before.generate(
        path_type=path_type, total_length=total_length,
        n_laser_pts=500, use_optimization=False, use_angle_factor=False)

    # 优化后: 等弧长采样 + 动态角度因子 (更均匀的点分布)
    traj_gen_after = TrajectoryGenerator(
        scan_width=scan_width, feed_rate=feed_rate, n_oscillation_cycles=15)
    result_after = traj_gen_after.generate(
        path_type=path_type, total_length=total_length,
        n_laser_pts=500, use_optimization=True, use_angle_factor=True)

    # 映射到网格坐标
    margin = 1.5e-3
    laser_pts_before = _map_to_grid(result_before["laser_points"],
                                     grid_w, grid_h, total_length, path_y_center, margin)
    laser_pts_after = _map_to_grid(result_after["laser_points"],
                                    grid_w, grid_h, total_length, path_y_center, margin)

    total_time = result_before["total_time"]
    traj_times = np.linspace(0, total_time, 500)

    # === 功率策略 ===
    p_opt = PowerOptimizer(base_power=laser_power)

    # 优化前: 恒定功率
    constant_power = np.full(500, laser_power)

    # 优化后: 根据AFTER轨迹的密度做功率补偿
    optimized_power, _, power_stats = p_opt.optimize(
        result_after["point_density"], strategy="inverse")

    # === 仿真优化前 (恒定功率 + 传统轨迹) ===
    sim_before = ThermalSimulator(material, grid)
    sim_before.set_trajectory(laser_pts_before, traj_times)
    snapshots_before, times_before = sim_before.run(
        total_time=total_time, dt=0.0005,
        laser_power=laser_power, beam_radius=beam_radius,
        snapshot_interval=50)

    # === 仿真优化后 (补偿功率 + 优化轨迹) ===
    sim_after = ThermalSimulator(material, grid)
    sim_after.set_trajectory(laser_pts_after, traj_times)
    snapshots_after, times_after = sim_after.run(
        total_time=total_time, dt=0.0005,
        laser_power=optimized_power, beam_radius=beam_radius,
        snapshot_interval=50)

    # === 提取数据 ===
    surf_before = sim_before.get_surface_temperature(-1)
    surf_after = sim_after.get_surface_temperature(-1)
    stats_before = sim_before.get_temperature_stats()
    stats_after = sim_after.get_temperature_stats()

    # === 优化指标 ===
    std_b = stats_before[-1]["std"]
    std_a = stats_after[-1]["std"]
    std_reduction = ((std_b - std_a) / std_b * 100) if std_b > 0 else 0.0

    max_b = stats_before[-1]["max"]
    max_a = stats_after[-1]["max"]
    if max_b > AMBIENT_TEMP:
        max_diff_reduction = ((max_b - max_a) / (max_b - AMBIENT_TEMP)) * 100
    else:
        max_diff_reduction = 0.0

    # === 切面温度剖面 (沿Y方向, 在工件中心X处) ===
    x_mid_idx = grid["nx"] // 2
    y_profile_before = surf_before[x_mid_idx, :]
    y_profile_after = surf_after[x_mid_idx, :]
    y_mm = np.linspace(0, grid_h * 1000, grid["ny"])  # mm

    return {
        "trajectory_before": {
            "points": laser_pts_before,
            "oscillation": result_before["oscillation"],
            "density": result_before["point_density"],
        },
        "trajectory_after": {
            "points": laser_pts_after,
            "oscillation": result_after["oscillation"],
            "density": result_after["point_density"],
        },
        "cutter_path": result_before["cutter_path"],
        "angle_factor": result_after["angle_factor"],

        "snapshots_before": snapshots_before,
        "snapshots_after": snapshots_after,
        "times_before": times_before,
        "times_after": times_after,

        "surface_before": surf_before,
        "surface_after": surf_after,

        "power_optimized": optimized_power,
        "power_constant": constant_power,
        "power_stats": power_stats,

        "temp_stats_before": stats_before,
        "temp_stats_after": stats_after,

        "std_reduction_pct": std_reduction,
        "max_diff_reduction_pct": max_diff_reduction,

        # Y方向温度剖面 (用于2D曲线对比)
        "y_mm": y_mm,
        "y_profile_before": y_profile_before,
        "y_profile_after": y_profile_after,

        "grid": grid,
        "material": material,
        "laser_power": laser_power,
        "beam_radius": beam_radius,
        "total_time": total_time,
    }


def _map_to_grid(points, grid_w, grid_h, orig_length, y_center, margin):
    """将轨迹点映射到网格坐标系"""
    pts = points.copy()
    x_min, x_max = pts[:, 0].min(), pts[:, 0].max()
    if x_max - x_min > 1e-12:
        pts[:, 0] = (pts[:, 0] - x_min) / (x_max - x_min) * (grid_w - 2 * margin) + margin
    else:
        pts[:, 0] = grid_w / 2

    y_min, y_max = pts[:, 1].min(), pts[:, 1].max()
    if y_max - y_min > 1e-12:
        scale = min((grid_h - 2 * margin) / (y_max - y_min), 1.5)
        pts[:, 1] = (pts[:, 1] - (y_min + y_max) / 2) * scale + y_center
    else:
        pts[:, 1] = y_center

    pts[:, 0] = np.clip(pts[:, 0], margin, grid_w - margin)
    pts[:, 1] = np.clip(pts[:, 1], margin, grid_h - margin)
    return pts
