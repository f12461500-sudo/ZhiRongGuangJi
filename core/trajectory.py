"""激光轨迹生成与优化算法

核心算法：
1. 传统正弦振荡轨迹 (优化前 - 产生"哑铃型"温度场)
2. 等弧长采样均匀化 (优化后核心算法)
3. 动态角度因子 (弯道/曲线处自动调整振幅)
4. 坐标变换 (激光跟随铣刀方向)
"""

import numpy as np
from scipy.interpolate import CubicSpline, interp1d


def generate_cutter_path(path_type, total_length, amplitude=0, n_points=500):
    """生成铣刀运动轨迹 (Xcutter, Ycutter)"""
    t = np.linspace(0, 1, n_points)

    if path_type == "直线":
        xc = np.linspace(0, total_length, n_points)
        yc = np.full(n_points, total_length * 0.25)

    elif path_type == "正弦曲线":
        xc = np.linspace(0, total_length, n_points)
        yc = total_length * 0.25 + amplitude * np.sin(2 * np.pi * t * 1.5)

    elif path_type == "S形曲线":
        xc = np.linspace(0, total_length, n_points)
        mid = n_points // 2
        yc = np.zeros(n_points) + total_length * 0.25
        yc[:mid] += amplitude * np.sin(np.pi * t[:mid])
        yc[mid:] -= amplitude * np.sin(np.pi * (t[mid:] - 0.5))

    else:
        raise ValueError(f"Unknown path type: {path_type}")

    return t, xc, yc


def compute_cutter_tangent(xc, yc):
    """计算铣刀切向角度 theta(t) [rad]"""
    dx = np.gradient(xc)
    dy = np.gradient(yc)
    return np.arctan2(dy, dx)


def compute_curvature(xc, yc):
    """计算轨迹曲率 kappa = |x'y'' - y'x''| / (x'^2 + y'^2)^(3/2)"""
    dx = np.gradient(xc)
    dy = np.gradient(yc)
    ddx = np.gradient(dx)
    ddy = np.gradient(dy)
    num = np.abs(dx * ddy - dy * ddx)
    den = (dx**2 + dy**2) ** 1.5 + 1e-12
    return num / den


def generate_sinusoidal_oscillation(xc, yc, amplitude, n_cycles, n_laser_pts):
    """生成传统正弦振荡激光轨迹 (优化前)

    均匀时间采样 -> 边缘密、中间疏 -> 哑铃型温度场

    Args:
        xc, yc: 铣刀路径坐标
        amplitude: 振荡振幅 (m)
        n_cycles: 振荡周期数 (如10-15次完整周期)
        n_laser_pts: 激光轨迹点数
    """
    n_cutter = len(xc)
    theta = compute_cutter_tangent(xc, yc)
    t_params = np.linspace(0, 1, n_laser_pts)

    # 插值到激光采样时间点
    t_cutter = np.linspace(0, 1, n_cutter)
    xc_interp = CubicSpline(t_cutter, xc)
    yc_interp = CubicSpline(t_cutter, yc)
    theta_interp = CubicSpline(t_cutter, theta)

    xc_l = xc_interp(t_params)
    yc_l = yc_interp(t_params)
    th_l = theta_interp(t_params)

    # 正弦振荡: ~n_cycles个完整周期
    oscillation = amplitude * np.sin(2 * np.pi * n_cycles * t_params)

    # 旋转到垂直于铣刀方向
    perp_x = -np.sin(th_l)
    perp_y = np.cos(th_l)

    x_laser = xc_l + oscillation * perp_x
    y_laser = yc_l + oscillation * perp_y

    return np.column_stack([x_laser, y_laser]), oscillation


def equal_arc_length_resample(points, n_output):
    """等弧长重采样 - 轨迹均匀化核心算法

    确保相邻点之间弧长相等，消除正弦振荡带来的点密度不均。
    """
    diffs = np.diff(points, axis=0)
    seg_lengths = np.sqrt(np.sum(diffs**2, axis=1))
    cum_arc = np.concatenate([[0], np.cumsum(seg_lengths)])
    total_arc = cum_arc[-1]

    if total_arc < 1e-15:
        return points[:n_output]

    target_arc = np.linspace(0, total_arc, n_output)
    x_new = np.interp(target_arc, cum_arc, points[:, 0])
    y_new = np.interp(target_arc, cum_arc, points[:, 1])
    return np.column_stack([x_new, y_new])


def generate_optimized_oscillation(xc, yc, amplitude, n_cycles, n_laser_pts,
                                    oversample_factor=10):
    """生成等弧长优化的激光振荡轨迹 (优化后)

    高密度生成正弦轨迹 -> 等弧长重采样 -> 均匀点分布 -> 均匀温度场
    """
    n_dense = n_laser_pts * oversample_factor
    n_cutter = len(xc)

    # 生成高密度传统轨迹
    dense_pts, _ = generate_sinusoidal_oscillation(
        xc, yc, amplitude, n_cycles, n_dense
    )

    # 等弧长重采样 -> 均匀分布
    uniform_pts = equal_arc_length_resample(dense_pts, n_laser_pts)

    # 计算优化后的振荡(投影回垂直方向用于显示)
    t_params = np.linspace(0, 1, n_laser_pts)
    t_cutter = np.linspace(0, 1, n_cutter)
    xc_interp = CubicSpline(t_cutter, xc)
    yc_interp = CubicSpline(t_cutter, yc)
    theta_interp = CubicSpline(t_cutter, compute_cutter_tangent(xc, yc))

    uniform_osc = np.zeros(n_laser_pts)
    for i, t in enumerate(t_params):
        dx = uniform_pts[i, 0] - xc_interp(t)
        dy = uniform_pts[i, 1] - yc_interp(t)
        th = theta_interp(t)
        uniform_osc[i] = dx * (-np.sin(th)) + dy * np.cos(th)

    return uniform_pts, uniform_osc


def dynamic_angle_factor(curvature, base_factor=0.5, sharpness_factor=2.0):
    """动态角度因子

    弯道处自动减弱激光振荡振幅，防止轨迹交叠和局部过热。
    angle_factor = 1 + base_factor * |kappa|^sharpness_factor
    """
    return 1.0 + base_factor * np.abs(curvature) ** sharpness_factor


def compute_point_density(points, kernel_width=None):
    """核密度估计计算轨迹点的局部密度 (归一化)"""
    n = len(points)
    if n < 2:
        return np.ones(n)

    if kernel_width is None:
        diffs = np.diff(points, axis=0)
        avg_dist = np.mean(np.sqrt(np.sum(diffs**2, axis=1)))
        kernel_width = avg_dist * 5

    # 高效计算：用局部窗口而非全局
    density = np.zeros(n)
    window = min(n - 1, max(10, int(kernel_width / (np.mean(np.diff(points[:, 0])) + 1e-12))))

    for i in range(n):
        lo = max(0, i - window)
        hi = min(n, i + window + 1)
        dists = np.sqrt(np.sum((points[lo:hi] - points[i]) ** 2, axis=1))
        density[i] = np.sum(np.exp(-0.5 * (dists / kernel_width) ** 2))

    density = density / max(np.mean(density), 1e-12)
    return density


class TrajectoryGenerator:
    """轨迹生成器"""

    def __init__(self, scan_width, feed_rate, n_oscillation_cycles=12):
        """
        Args:
            scan_width: 扫描宽度 (m) - 振幅 = scan_width/2
            feed_rate: 进给速度 (m/s)
            n_oscillation_cycles: 全程振荡周期数 (影响密度对比度)
        """
        self.amplitude = scan_width / 2.0
        self.feed_rate = feed_rate
        self.n_cycles = n_oscillation_cycles

    def generate(self, path_type, total_length, n_laser_pts=400,
                 use_optimization=True, use_angle_factor=True):
        """生成完整激光轨迹数据

        Returns:
            dict with laser_points, oscillation, cutter_path, point_density, etc.
        """
        cutter_amp = total_length * 0.12
        t_norm, xc, yc = generate_cutter_path(
            path_type, total_length, amplitude=cutter_amp, n_points=500
        )

        if use_optimization:
            laser_pts, oscillation = generate_optimized_oscillation(
                xc, yc, self.amplitude, self.n_cycles, n_laser_pts
            )
        else:
            laser_pts, oscillation = generate_sinusoidal_oscillation(
                xc, yc, self.amplitude, self.n_cycles, n_laser_pts
            )

        # 动态角度因子 (弯道适配)
        curvature = compute_curvature(xc, yc)
        angle_factor = dynamic_angle_factor(curvature)

        if use_angle_factor and path_type != "直线":
            t_cutter = np.linspace(0, 1, len(xc))
            t_laser = np.linspace(0, 1, n_laser_pts)
            af_interp = interp1d(t_cutter, angle_factor, kind='linear',
                                  fill_value='extrapolate')
            af_at_laser = af_interp(t_laser)

            oscillation_adj = oscillation / af_at_laser

            xc_interp = CubicSpline(t_cutter, xc)
            yc_interp = CubicSpline(t_cutter, yc)
            theta_interp = CubicSpline(t_cutter, compute_cutter_tangent(xc, yc))

            xc_l = xc_interp(t_laser)
            yc_l = yc_interp(t_laser)
            th_l = theta_interp(t_laser)

            perp_x = -np.sin(th_l)
            perp_y = np.cos(th_l)
            laser_pts = np.column_stack([
                xc_l + oscillation_adj * perp_x,
                yc_l + oscillation_adj * perp_y
            ])
            oscillation = oscillation_adj

        density = compute_point_density(laser_pts)

        diffs = np.diff(laser_pts, axis=0)
        total_arc = np.sum(np.sqrt(np.sum(diffs**2, axis=1)))
        total_time = total_length / self.feed_rate

        return {
            "laser_points": laser_pts,
            "oscillation": oscillation,
            "cutter_path": np.column_stack([xc, yc]),
            "point_density": density,
            "angle_factor": angle_factor,
            "total_arc_length": total_arc,
            "total_time": total_time,
            "n_points": n_laser_pts,
        }
