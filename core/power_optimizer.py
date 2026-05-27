"""功率优化模块 - PWM模拟 + 密度补偿 + 简化神经网络代理模型

核心思路:
1. 轨迹点密度高 -> 该区域能量输入过剩 -> 降低功率
2. 轨迹点密度低 -> 该区域能量输入不足 -> 增加功率
3. 最终使每个轨迹点贡献的能量均匀，实现"冷区加功率、热区降功率"
"""

import numpy as np


def compute_pwm_power(base_power, density, strategy="inverse"):
    """根据点密度计算PWM功率补偿

    Args:
        base_power: 基础激光功率 (W)
        density: 归一化点密度 (density/mean, 1.0=平均密度)
        strategy: "inverse" - P ~ 1/density (完全补偿)
                  "proportional" - P ~ 1/sqrt(density) (部分补偿)
    Returns:
        power_curve: 每个轨迹点的目标功率 (W)
    """
    density = np.clip(density, 0.3, 3.0)  # 限制范围防止极端值

    if strategy == "inverse":
        compensation = 1.0 / density
    elif strategy == "proportional":
        compensation = 1.0 / np.sqrt(density)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    # 归一化补偿因子，使平均功率 = base_power
    compensation = compensation / np.mean(compensation)
    power_curve = base_power * compensation

    return power_curve


def generate_pwm_signal(power_curve, pwm_frequency=5000, sample_rate=50000):
    """生成PWM控制信号 (用于可视化)

    Args:
        power_curve: 目标功率序列
        pwm_frequency: PWM频率 (Hz)
        sample_rate: 输出采样率 (Hz)
    Returns:
        t_pwm: 时间序列
        pwm_signal: PWM方波信号
        duty_cycle: 占空比序列
    """
    n_traj = len(power_curve)
    total_time = n_traj * (1.0 / pwm_frequency)  # 简化: 每个轨迹点对应一个PWM周期

    t_pwm = np.linspace(0, total_time, int(total_time * sample_rate))
    pwm_signal = np.zeros_like(t_pwm)
    duty_cycle = np.zeros(n_traj)

    max_power = np.max(power_curve)
    if max_power == 0:
        max_power = 1.0

    for i in range(n_traj):
        duty = np.clip(power_curve[i] / max_power, 0.0, 1.0)
        duty_cycle[i] = duty

        # 在每个PWM周期内生成方波
        t_start = i / pwm_frequency
        t_end = (i + 1) / pwm_frequency
        mask = (t_pwm >= t_start) & (t_pwm < t_start + duty / pwm_frequency)
        pwm_signal[mask] = max_power

    return t_pwm, pwm_signal, duty_cycle


class PowerOptimizer:
    """功率优化器 - 封装功率优化逻辑"""

    def __init__(self, base_power, max_power=None, min_power=None):
        """
        Args:
            base_power: 基础激光功率 (W)
            max_power: 最大功率限制 (W), 默认 = base_power * 1.5
            min_power: 最小功率限制 (W), 默认 = base_power * 0.3
        """
        self.base_power = base_power
        self.max_power = max_power or base_power * 1.5
        self.min_power = min_power or base_power * 0.3

    def optimize(self, point_density, strategy="inverse"):
        """根据点密度优化功率

        Args:
            point_density: 归一化点密度数组
            strategy: 补偿策略
        Returns:
            optimized_power: 优化后的功率曲线
            constant_power: 恒定功率曲线 (用于对比)
            stats: 功率统计信息
        """
        constant_power = np.full(len(point_density), self.base_power)
        optimized_power = compute_pwm_power(self.base_power, point_density, strategy)
        optimized_power = np.clip(optimized_power, self.min_power, self.max_power)

        stats = {
            "base_power": self.base_power,
            "optimized_mean": float(np.mean(optimized_power)),
            "optimized_min": float(np.min(optimized_power)),
            "optimized_max": float(np.max(optimized_power)),
            "power_variation": float(np.std(optimized_power)),
            "power_range_ratio": float((np.max(optimized_power) - np.min(optimized_power))
                                        / self.base_power),
        }

        return optimized_power, constant_power, stats


def neural_surrogate_predict(temperature_target, material_props, model_type="linear"):
    """简化"神经网络"代理模型 - 替代真实TensorFlow模型

    在Demo中，我们使用物理规则+插值来模拟神经网络的预测功能。
    真实部署时替换为训练好的TensorFlow模型。

    Args:
        temperature_target: 目标温度场描述 {"target_max": float, "target_uniformity": float}
        material_props: 材料属性
        model_type: 模型类型 ("linear" | "rule_based")
    Returns:
        predicted_params: {"power": float, "scan_speed": float, "beam_radius": float}
    """
    if model_type == "linear":
        # 简化: 线性响应面
        target_max = temperature_target.get("target_max", 700)
        absorptivity = material_props.get("absorptivity", 0.4)
        conductivity = material_props.get("thermal_conductivity", 7.0)

        power = target_max * conductivity / (absorptivity * 100)
        scan_speed = 10.0 + (target_max - 400) * 0.02
        beam_radius = 1.0 + (target_max - 400) * 0.001

        return {
            "power": max(100, min(2000, power)),
            "scan_speed": max(5, min(30, scan_speed)),
            "beam_radius": max(0.5, min(3.0, beam_radius)),
        }

    else:  # rule_based
        # 基于经验规则的参数推荐
        target_max = temperature_target.get("target_max", 700)
        target_uniformity = temperature_target.get("target_uniformity", 0.1)

        if target_max < 500:
            power, speed, beam = 200, 20, 2.0
        elif target_max < 800:
            power, speed, beam = 350, 15, 1.5
        elif target_max < 1100:
            power, speed, beam = 500, 12, 1.2
        else:
            power, speed, beam = 700, 8, 1.0

        # 均匀性要求越高，光束越大
        beam *= (1.0 + target_uniformity * 5)

        return {
            "power": power,
            "scan_speed": speed,
            "beam_radius": beam,
        }
