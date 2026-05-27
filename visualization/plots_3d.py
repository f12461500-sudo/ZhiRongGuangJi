"""3D温度场可视化: 表面热力图、3D surface、时间演化"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np


def plot_surface_heatmap(temp_field, x_mm, y_mm, title="表面温度场",
                          colorscale="Hot", zmin=None, zmax=None):
    """2D热力图显示表面温度场

    Args:
        temp_field: [ny, nx] 温度场 (注意: plotly heatmap的z是[row, col])
        x_mm, y_mm: 坐标轴 (mm)
        title: 标题
        colorscale: 色阶
    """
    z = temp_field.copy()
    if zmin is None:
        zmin = z.min()
    if zmax is None:
        zmax = z.max()

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=x_mm,
        y=y_mm,
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        colorbar=dict(title="温度 (°C)" if "temp" in title.lower() else "能量"),
        hovertemplate='X: %{x:.1f}mm<br>Y: %{y:.1f}mm<br>值: %{z:.1f}<extra></extra>',
    ))

    fig.update_layout(
        title=title,
        xaxis_title='X (mm)',
        yaxis_title='Y (mm)',
        xaxis=dict(scaleanchor='y', scaleratio=1),
        height=450,
        margin=dict(l=50, r=30, t=50, b=50),
        template='plotly_white',
    )
    return fig


def plot_3d_surface(temp_field, x_mm, y_mm, title="3D温度场",
                     colorscale="Hot", zmin=None, zmax=None):
    """3D surface plot显示温度场"""
    z = temp_field.copy()
    if zmin is None:
        zmin = z.min()
    if zmax is None:
        zmax = z.max()

    fig = go.Figure(data=go.Surface(
        z=z,
        x=x_mm,
        y=y_mm,
        colorscale=colorscale,
        cmin=zmin,
        cmax=zmax,
        colorbar=dict(title="温度 (°C)"),
        contours={
            "z": {"show": True, "usecolormap": True, "highlightcolor": "limegreen",
                  "project": {"z": True}}
        },
    ))

    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title='X (mm)',
            yaxis_title='Y (mm)',
            zaxis_title='温度 (°C)',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2)),
            aspectratio=dict(x=1.5, y=1, z=0.8),
        ),
        height=500,
        margin=dict(l=0, r=0, t=50, b=0),
        template='plotly_white',
    )
    return fig


def plot_before_after_heatmaps(temp_before, temp_after, x_mm, y_mm,
                                vmin=None, vmax=None):
    """优化前/后温度场并排对比热力图"""
    if vmin is None:
        vmin = min(temp_before.min(), temp_after.min())
    if vmax is None:
        vmax = max(temp_before.max(), temp_after.max())

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("优化前 (传统扫描)", "优化后 (智能补偿)"),
        horizontal_spacing=0.12,
    )

    fig.add_trace(go.Heatmap(
        z=temp_before, x=x_mm, y=y_mm,
        colorscale="Hot", zmin=vmin, zmax=vmax,
        colorbar=dict(title="", x=0.455),
        name="优化前",
    ), row=1, col=1)

    fig.add_trace(go.Heatmap(
        z=temp_after, x=x_mm, y=y_mm,
        colorscale="Hot", zmin=vmin, zmax=vmax,
        colorbar=dict(title="温度 (°C)"),
        name="优化后",
    ), row=1, col=2)

    fig.update_layout(
        title="表面温度场对比: 优化前 (哑铃型) vs 优化后 (香肠型)",
        height=400,
        margin=dict(l=30, r=30, t=60, b=40),
        template='plotly_white',
    )
    # 强制等比例
    fig.update_xaxes(scaleanchor='y', scaleratio=1, title_text='X (mm)')
    fig.update_yaxes(title_text='Y (mm)')
    return fig


def plot_temperature_evolution(snapshots, times, x_mm, y_mm,
                                frame_indices=None, title="温度场时间演化"):
    """创建带时间滑块的温度演化图

    Args:
        snapshots: list of [nx, ny, nz] arrays
        times: time values (s)
        x_mm, y_mm: coordinates
        frame_indices: which snapshot indices to include (default: all)
    """
    if frame_indices is None:
        step = max(1, len(snapshots) // 30)
        frame_indices = list(range(0, len(snapshots), step))
        if frame_indices[-1] != len(snapshots) - 1:
            frame_indices.append(len(snapshots) - 1)

    # 提取各帧表面温度
    surface_temps = []
    for idx in frame_indices:
        surf = snapshots[idx][:, :, 0]  # z=0 surface
        surface_temps.append(surf)

    all_temps = np.array([s.max() for s in surface_temps])
    zmax = all_temps.max()
    zmin = 25  # ambient

    # 构建帧
    frames = []
    for i, idx in enumerate(frame_indices):
        frames.append(go.Frame(
            data=[go.Heatmap(
                z=surface_temps[i],
                x=x_mm, y=y_mm,
                colorscale="Hot",
                zmin=zmin, zmax=zmax,
            )],
            name=f"t={times[idx]:.2f}s",
        ))

    fig = go.Figure(
        data=[go.Heatmap(
            z=surface_temps[0],
            x=x_mm, y=y_mm,
            colorscale="Hot",
            zmin=zmin, zmax=zmax,
            colorbar=dict(title="温度 (°C)"),
        )],
        frames=frames,
    )

    # 播放控件
    n_frames = len(frames)
    fig.update_layout(
        title=title,
        xaxis_title='X (mm)', yaxis_title='Y (mm)',
        xaxis=dict(scaleanchor='y', scaleratio=1),
        height=450,
        margin=dict(l=40, r=30, t=50, b=40),
        template='plotly_white',
        updatemenus=[{
            "type": "buttons",
            "buttons": [
                {"label": "播放", "method": "animate",
                 "args": [None, {"frame": {"duration": 100, "redraw": True},
                                 "fromcurrent": True}]},
                {"label": "暂停", "method": "animate",
                 "args": [[None], {"frame": {"duration": 0, "redraw": False},
                                  "mode": "immediate"}]},
            ],
            "x": 0.1, "y": -0.1,
        }],
    )

    # 时间滑块
    sliders = [{
        "steps": [{
            "args": [[f"t={times[frame_indices[k]]:.2f}s"],
                     {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": f"{times[frame_indices[k]]:.1f}s",
            "method": "animate",
        } for k in range(n_frames)],
        "currentvalue": {"prefix": "时间: "},
        "len": 0.9, "x": 0.05, "y": -0.15,
    }]

    fig.update_layout(sliders=sliders)
    return fig
