"""能量沉积快速预览模型

通过计算轨迹点密度 -> 能量沉积分布 -> 温度场代理
可在1秒内生成对比效果，用于快速参数探索和Demo展示。
"""

import numpy as np
from scipy.ndimage import gaussian_filter
from core.trajectory import TrajectoryGenerator
from core.power_optimizer import PowerOptimizer


def compute_energy_field(trajectory_points, power_curve, grid_w, grid_h,
                          beam_radius, resolution=0.2e-3):
    """计算表面能量沉积场 [J/m²]

    将每个轨迹点的高斯热流在2D网格上累加。

    Args:
        trajectory_points: [(x,y), ...] (m)
        power_curve: [P1, P2, ...] (W) 每个点的功率
        grid_w, grid_h: 网格物理尺寸 (m)
        beam_radius: 光斑半径 (m)
        resolution: 输出分辨率 (m)
    Returns:
        energy_2d: [ny, nx] 能量密度场
        x_edges, y_edges: 用于pcolormesh的边缘坐标
    """
    nx = int(grid_w / resolution) + 1
    ny = int(grid_h / resolution) + 1

    energy = np.zeros((ny, nx))
    dwell_time = 0.005  # 每个点的驻留时间 (s) - 简化假设

    for i, (px, py) in enumerate(trajectory_points):
        xi = int(px / resolution)
        yi = int(py / resolution)
        power = power_curve[i] if hasattr(power_curve, "__len__") else power_curve

        if 0 <= xi < nx and 0 <= yi < ny:
            # 在光斑范围内累加高斯能量
            r_cells = int(beam_radius * 2.5 / resolution)  # 2.5倍半径范围
            x_min = max(0, xi - r_cells)
            x_max = min(nx, xi + r_cells + 1)
            y_min = max(0, yi - r_cells)
            y_max = min(ny, yi + r_cells + 1)

            xx, yy = np.meshgrid(
                np.arange(x_min, x_max) * resolution,
                np.arange(y_min, y_max) * resolution,
                indexing='xy'
            )
            r2 = (xx - px) ** 2 + (yy - py) ** 2
            gaussian = np.exp(-2.0 * r2 / beam_radius ** 2)
            energy[y_min:y_max, x_min:x_max] += gaussian * power * dwell_time

    # 平滑处理 (模拟热扩散的最小效果)
    sigma = beam_radius / resolution * 0.8
    energy = gaussian_filter(energy, sigma=sigma)

    x_edges = np.linspace(0, grid_w, nx + 1)
    y_edges = np.linspace(0, grid_h, ny + 1)

    return energy, x_edges, y_edges


def map_energy_to_temperature(energy_field, base_temp=25.0, max_temp=800.0):
    """将能量场映射到温度范围"""
    e_min, e_max = energy_field.min(), energy_field.max()
    if e_max - e_min < 1e-12:
        return np.full_like(energy_field, base_temp)
    return base_temp + (energy_field - e_min) / (e_max - e_min) * (max_temp - base_temp)


def run_energy_comparison(path_type, laser_power, beam_radius, scan_width, feed_rate,
                           grid_w=20e-3, grid_h=16e-3, n_pts=500, resolution=0.15e-3):
    """运行能量沉积对比: 优化前 vs 优化后 (快速模式, <1秒)

    Returns:
        dict with energy fields, temperature maps, and comparison metrics
    """
    total_length = grid_w * 0.75
    center_y = grid_h / 2

    # === 优化前: 传统轨迹 + 恒定功率 ===
    gen_before = TrajectoryGenerator(scan_width, feed_rate, n_oscillation_cycles=10)
    r_before = gen_before.generate(path_type, total_length, n_pts,
                                    use_optimization=False, use_angle_factor=False)

    pts_before = r_before["laser_points"]
    margin = 1.5e-3
    pts_b = _scale_points(pts_before, grid_w, grid_h, center_y, margin)
    const_power = np.full(n_pts, laser_power)

    energy_before, x_e, y_e = compute_energy_field(
        pts_b, const_power, grid_w, grid_h, beam_radius, resolution)

    # === 优化后: 优化轨迹 + 密度补偿功率 ===
    gen_after = TrajectoryGenerator(scan_width, feed_rate, n_oscillation_cycles=10)
    r_after = gen_after.generate(path_type, total_length, n_pts,
                                  use_optimization=True, use_angle_factor=True)

    pts_after = r_after["laser_points"]
    pts_a = _scale_points(pts_after, grid_w, grid_h, center_y, margin)

    density_after = r_after["point_density"]
    p_opt = PowerOptimizer(base_power=laser_power)
    opt_power, _, power_stats = p_opt.optimize(density_after, "inverse")

    energy_after, _, _ = compute_energy_field(
        pts_a, opt_power, grid_w, grid_h, beam_radius, resolution)

    # === 映射到温度 ===
    max_temp = laser_power * 1.5
    temp_before = map_energy_to_temperature(energy_before, max_temp=max_temp)
    temp_after = map_energy_to_temperature(energy_after, max_temp=max_temp)

    # === 指标 ===
    # 扫描带内的均匀性
    scan_half = int((scan_width / 2) / grid_h * energy_before.shape[0])
    cy = energy_before.shape[0] // 2
    band_start = max(0, cy - scan_half)
    band_end = min(energy_before.shape[0], cy + scan_half)

    band_b = energy_before[band_start:band_end, :]
    band_a = energy_after[band_start:band_end, :]

    std_b = band_b.std()
    std_a = band_a.std()
    std_reduction = ((std_b - std_a) / std_b * 100) if std_b > 0 else 0.0

    # Y方向剖面 (沿中心X)
    x_mid = energy_before.shape[1] // 2
    y_profile_b = energy_before[:, x_mid]
    y_profile_a = energy_after[:, x_mid]
    y_mm = np.linspace(0, grid_h * 1000, len(y_profile_b))

    return {
        "energy_before": energy_before,
        "energy_after": energy_after,
        "temp_before": temp_before,
        "temp_after": temp_after,
        "x_edges_mm": x_e * 1000,
        "y_edges_mm": y_e * 1000,
        "x_mm": (x_e[:-1] + x_e[1:]) / 2 * 1000,
        "y_mm": y_mm,

        "trajectory_before": {"points": pts_b, "density": r_before["point_density"]},
        "trajectory_after": {"points": pts_a, "density": r_after["point_density"]},

        "power_optimized": opt_power,
        "power_constant": const_power,
        "power_stats": power_stats,

        "std_reduction_pct": std_reduction,
        "y_profile_before": y_profile_b,
        "y_profile_after": y_profile_a,
    }


def _scale_points(points, grid_w, grid_h, center_y, margin):
    pts = points.copy()
    x_min, x_max = pts[:, 0].min(), pts[:, 0].max()
    if x_max - x_min > 1e-12:
        pts[:, 0] = (pts[:, 0] - x_min) / (x_max - x_min) * (grid_w - 2 * margin) + margin
    else:
        pts[:, 0] = grid_w / 2
    pts[:, 1] = pts[:, 1] - pts[:, 1].mean() + center_y
    pts[:, 0] = np.clip(pts[:, 0], margin, grid_w - margin)
    pts[:, 1] = np.clip(pts[:, 1], margin, grid_h - margin)
    return pts
