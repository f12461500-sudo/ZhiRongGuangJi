"""2D图表: 轨迹路径、功率曲线、温度剖面"""

import plotly.graph_objects as go
import numpy as np


def plot_trajectory(laser_points, cutter_path=None, title="激光扫描轨迹"):
    """绘制2D轨迹对比图"""
    fig = go.Figure()

    if cutter_path is not None:
        fig.add_trace(go.Scatter(
            x=cutter_path[:, 0] * 1000, y=cutter_path[:, 1] * 1000,
            mode='lines', name='铣刀路径',
            line=dict(color='gray', width=2, dash='dash'),
        ))

    fig.add_trace(go.Scatter(
        x=laser_points[:, 0] * 1000, y=laser_points[:, 1] * 1000,
        mode='lines', name='激光轨迹',
        line=dict(color='#FF4444', width=1.5),
    ))

    fig.update_layout(
        title=title,
        xaxis_title='X (mm)', yaxis_title='Y (mm)',
        xaxis=dict(scaleanchor='y', scaleratio=1),
        height=400, margin=dict(l=40, r=20, t=50, b=40),
        template='plotly_white',
    )
    return fig


def plot_trajectory_comparison(pts_before, pts_after, title="轨迹对比: 优化前 vs 优化后"):
    """优化前后轨迹并排对比"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=pts_before[:, 0] * 1000, y=pts_before[:, 1] * 1000,
        mode='lines', name='优化前 (传统)',
        line=dict(color='#FF6B6B', width=1.5),
        visible=True,
    ))
    fig.add_trace(go.Scatter(
        x=pts_after[:, 0] * 1000, y=pts_after[:, 1] * 1000,
        mode='lines', name='优化后 (等弧长)',
        line=dict(color='#4ECDC4', width=1.5),
        visible=True,
    ))

    fig.update_layout(
        title=title,
        xaxis_title='X (mm)', yaxis_title='Y (mm)',
        xaxis=dict(scaleanchor='y', scaleratio=1),
        height=420, margin=dict(l=40, r=20, t=50, b=40),
        template='plotly_white',
    )
    return fig


def plot_point_density(density_before, density_after):
    """点密度分布对比"""
    fig = go.Figure()

    x = np.arange(len(density_before))
    fig.add_trace(go.Scatter(
        x=x, y=density_before, mode='lines',
        name='优化前', line=dict(color='#FF6B6B', width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=x, y=density_after, mode='lines',
        name='优化后', line=dict(color='#4ECDC4', width=1.5),
    ))
    fig.add_hline(y=1.0, line_dash="dash", line_color="gray",
                   annotation_text="平均密度")

    fig.update_layout(
        title="轨迹点密度分布 (归一化)",
        xaxis_title="轨迹点序号", yaxis_title="相对密度",
        height=300, margin=dict(l=40, r=20, t=50, b=40),
        template='plotly_white',
    )
    return fig


def plot_power_curve(constant_power, optimized_power):
    """功率曲线对比"""
    fig = go.Figure()

    n = len(constant_power)
    x = np.arange(n)

    fig.add_trace(go.Scatter(
        x=x, y=constant_power, mode='lines',
        name='恒定功率 (优化前)',
        line=dict(color='#FF6B6B', width=2),
    ))
    fig.add_trace(go.Scatter(
        x=x, y=optimized_power, mode='lines',
        name='优化功率 (优化后)',
        line=dict(color='#4ECDC4', width=2),
    ))

    base = np.mean(constant_power)
    fig.add_hline(y=base, line_dash="dash", line_color="gray",
                   annotation_text=f"{base:.0f}W")

    fig.update_layout(
        title="激光功率控制曲线",
        xaxis_title="轨迹点序号", yaxis_title="功率 (W)",
        height=320, margin=dict(l=40, r=20, t=50, b=40),
        template='plotly_white',
    )
    return fig


def plot_y_temperature_profile(y_mm, profile_before, profile_after):
    """Y方向温度剖面 (展示哑铃型 vs 香肠型)"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=y_mm, y=profile_before, mode='lines',
        name='优化前 (哑铃型)',
        line=dict(color='#FF6B6B', width=2.5),
        fill='tozeroy', fillcolor='rgba(255,107,107,0.1)',
    ))
    fig.add_trace(go.Scatter(
        x=y_mm, y=profile_after, mode='lines',
        name='优化后 (香肠型)',
        line=dict(color='#4ECDC4', width=2.5),
        fill='tozeroy', fillcolor='rgba(78,205,196,0.1)',
    ))

    fig.update_layout(
        title="Y方向能量/温度剖面 (工件中心截面)",
        xaxis_title="Y位置 (mm)", yaxis_title="相对能量/温度",
        height=320, margin=dict(l=40, r=20, t=50, b=40),
        template='plotly_white',
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99),
    )
    return fig


def plot_pwm_signal(t_pwm, pwm_signal, duty_cycle):
    """PWM信号可视化"""
    # 只显示前1000个点避免过载
    n_show = min(1000, len(t_pwm))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t_pwm[:n_show] * 1000, y=pwm_signal[:n_show],
        mode='lines', name='PWM信号',
        line=dict(color='#3498db', width=1),
    ))
    fig.update_layout(
        title=f"PWM控制信号 (占空比: {duty_cycle.mean():.1%})",
        xaxis_title="时间 (ms)", yaxis_title="功率 (W)",
        height=250, margin=dict(l=40, r=20, t=50, b=40),
        template='plotly_white',
    )
    return fig
