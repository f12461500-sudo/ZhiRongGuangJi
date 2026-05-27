"""3D有限差分热传导仿真引擎 + 高斯光束热源模型

采用表面热流 (Surface Heat Flux) 边界条件模拟激光加热，
比体积热源模型更接近真实的激光加工物理过程。
"""

import numpy as np
from core.config import AMBIENT_TEMP, CONVECTION_COEFF


def gaussian_flux(x, y, cx, cy, power, beam_radius, absorptivity):
    """计算高斯表面热流密度 [W/m²]
    q(r) = (2*P*eta)/(pi*r0^2) * exp(-2*r^2/r0^2)
    """
    r2 = (x - cx) ** 2 + (y - cy) ** 2
    coeff = (2.0 * power * absorptivity) / (np.pi * beam_radius ** 2)
    return coeff * np.exp(-2.0 * r2 / beam_radius ** 2)


class ThermalSimulator:
    """3D显式有限差分热传导求解器 (表面热流边界)"""

    def __init__(self, material, grid_params):
        """
        Args:
            material: dict with density, specific_heat, thermal_conductivity, absorptivity
            grid_params: dict with nx, ny, nz, dx, dy, dz
        """
        self.rho = material["density"]
        self.cp = material["specific_heat"]
        self.k = material["thermal_conductivity"]
        self.absorptivity = material["absorptivity"]

        self.nx = grid_params["nx"]
        self.ny = grid_params["ny"]
        self.nz = grid_params["nz"]
        self.dx = grid_params["dx"]
        self.dy = grid_params["dy"]
        self.dz = grid_params["dz"]

        # 热扩散率 alpha = k/(rho*cp)
        self.alpha = self.k / (self.rho * self.cp)

        # 网格物理坐标 (中心对齐)
        self.x = np.linspace(0, (self.nx - 1) * self.dx, self.nx)
        self.y = np.linspace(0, (self.ny - 1) * self.dy, self.ny)
        self.z = np.linspace(0, (self.nz - 1) * self.dz, self.nz)
        self.X_surf, self.Y_surf = np.meshgrid(self.x, self.y, indexing="ij")

        # 仿真状态
        self.T = None
        self.snapshots = []
        self.snapshot_times = []
        self.trajectory = None
        self.trajectory_times = None

    def _stability_check(self, dt):
        """3D显式FDM稳定性: alpha*dt*(1/dx²+1/dy²+1/dz²) <= 0.5"""
        limit = 0.5 / (self.alpha * (1 / self.dx**2 + 1 / self.dy**2 + 1 / self.dz**2))
        if dt > limit:
            return False, limit
        return True, limit

    def set_trajectory(self, points, times):
        """设置激光扫描轨迹 (物理坐标, 单位: m)"""
        self.trajectory = np.array(points)
        self.trajectory_times = np.array(times)

    def _get_laser_position(self, t):
        """线性插值获取t时刻的激光位置"""
        if self.trajectory is None or len(self.trajectory) == 0:
            return self.x.mean(), self.y.mean()

        if t <= self.trajectory_times[0]:
            return float(self.trajectory[0, 0]), float(self.trajectory[0, 1])
        if t >= self.trajectory_times[-1]:
            return float(self.trajectory[-1, 0]), float(self.trajectory[-1, 1])

        idx = np.searchsorted(self.trajectory_times, t) - 1
        idx = max(0, min(idx, len(self.trajectory_times) - 2))
        frac = (t - self.trajectory_times[idx]) / (
            self.trajectory_times[idx + 1] - self.trajectory_times[idx] + 1e-12
        )
        cx = self.trajectory[idx, 0] + frac * (self.trajectory[idx + 1, 0] - self.trajectory[idx, 0])
        cy = self.trajectory[idx, 1] + frac * (self.trajectory[idx + 1, 1] - self.trajectory[idx, 1])
        return cx, cy

    def run(self, total_time, dt, laser_power, beam_radius,
            snapshot_interval=40, progress_callback=None):
        """运行瞬态热传导仿真

        Args:
            total_time: 总仿真时间 (s)
            dt: 时间步长 (s)
            laser_power: 激光功率 (W) - 支持随时间变化的array
            beam_radius: 光斑半径 (m)
            snapshot_interval: 记录快照间隔(步数)
            progress_callback: 可选进度回调
        Returns:
            snapshots, snapshot_times
        """
        ok, limit = self._stability_check(dt)
        if not ok:
            dt = limit * 0.9

        # 初始化
        self.T = np.full((self.nx, self.ny, self.nz), AMBIENT_TEMP, dtype=np.float64)
        total_steps = int(total_time / dt)
        self.snapshots = []
        self.snapshot_times = []

        # 记录初始状态
        self.snapshots.append(self.T.copy())
        self.snapshot_times.append(0.0)

        # 预计算FDM系数
        rx = self.alpha * dt / self.dx**2
        ry = self.alpha * dt / self.dy**2
        rz = self.alpha * dt / self.dz**2

        # 顶面热流系数: flux * dt / (rho * cp * dz)
        flux_coeff = dt / (self.rho * self.cp * self.dz)

        for step in range(1, total_steps + 1):
            t = step * dt

            # 当前激光功率 (支持标量或时变)
            power = laser_power
            if hasattr(laser_power, "__len__"):
                idx = min(int(t / total_time * len(laser_power)), len(laser_power) - 1)
                power = laser_power[idx]

            T_old = self.T

            # === 3D Laplacian (内部导热) ===
            d2x = (np.roll(T_old, -1, axis=0) - 2 * T_old + np.roll(T_old, 1, axis=0)) / self.dx**2
            d2y = (np.roll(T_old, -1, axis=1) - 2 * T_old + np.roll(T_old, 1, axis=1)) / self.dy**2
            d2z = (np.roll(T_old, -1, axis=2) - 2 * T_old + np.roll(T_old, 1, axis=2)) / self.dz**2

            self.T = T_old + self.alpha * dt * (d2x + d2y + d2z)

            # === 顶面边界: 激光热流 + 对流冷却 ===
            cx, cy = self._get_laser_position(t)
            flux = gaussian_flux(self.X_surf, self.Y_surf, cx, cy,
                                 power, beam_radius, self.absorptivity)
            # 激光加热 (正热流)
            self.T[:, :, 0] += flux * flux_coeff
            # 对流冷却 (向环境散热)
            self.T[:, :, 0] += (
                CONVECTION_COEFF * dt / (self.rho * self.cp * self.dz)
                * (AMBIENT_TEMP - T_old[:, :, 0])
            )

            # === 侧面和底面: 固定环境温度 ===
            self.T[0, :, :] = AMBIENT_TEMP
            self.T[-1, :, :] = AMBIENT_TEMP
            self.T[:, 0, :] = AMBIENT_TEMP
            self.T[:, -1, :] = AMBIENT_TEMP
            self.T[:, :, -1] = AMBIENT_TEMP

            # 记录快照
            if step % snapshot_interval == 0:
                self.snapshots.append(self.T.copy())
                self.snapshot_times.append(t)

            if progress_callback and step % 200 == 0:
                progress_callback(step, total_steps)

        self.T_final = self.T.copy()
        return self.snapshots, self.snapshot_times

    def get_surface_temperature(self, snapshot_idx=-1):
        """顶面温度分布 (z=0)"""
        if self.snapshots:
            return self.snapshots[snapshot_idx][:, :, 0]
        return None

    def get_cross_section(self, axis="y", position=0.5, snapshot_idx=-1):
        """指定截面温度分布"""
        if not self.snapshots:
            return None
        T = self.snapshots[snapshot_idx]
        if axis == "x":
            idx = int(position * (self.nx - 1))
            return T[idx, :, :]
        elif axis == "y":
            idx = int(position * (self.ny - 1))
            return T[:, idx, :]
        else:
            idx = int(position * (self.nz - 1))
            return T[:, :, idx]

    def get_temperature_stats(self):
        """所有快照的温度统计"""
        return [{
            "max": float(np.max(T)),
            "min": float(np.min(T)),
            "mean": float(np.mean(T)),
            "std": float(np.std(T)),
        } for T in self.snapshots]

    def get_surface_line_profile(self, snapshot_idx=-1, axis="x", position=0.5):
        """获取表面某条线的温度剖面 (用于2D曲线)"""
        surf = self.get_surface_temperature(snapshot_idx)
        if surf is None:
            return None, None
        if axis == "x":
            idx = int(position * (self.ny - 1))
            return self.x * 1000, surf[:, idx]  # 转为mm
        else:
            idx = int(position * (self.nx - 1))
            return self.y * 1000, surf[idx, :]
