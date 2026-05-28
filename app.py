"""智融光迹控制软件 v2.0 — 答辩增强版
- 深色专业主题
- 拖拽对比滑块（哑铃型 vs 香肠型）
- 一键自动演示模式
- 动态指标卡片
- 实时参数调节
"""

import streamlit as st
import numpy as np
import time

st.set_page_config(
    page_title="智融光迹 | 激光轨迹优化",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.config import MATERIALS, DEFAULT_LASER, DEFAULT_GRID
from core.energy_deposition import run_energy_comparison
from core.simulation_pipeline import run_comparison_simulation
from visualization import plots_2d, plots_3d
from visualization.comparison import show_optimization_summary
from data.demo_scenarios import DEMO_SCENARIOS, get_demo_list

# ============================================================
# 自定义 CSS
# ============================================================
st.markdown("""
<style>
/* === 全局 === */
.main { padding-top: 0; }
.stApp { background: linear-gradient(180deg, #0D1117 0%, #161B22 100%); }

/* === 指标卡片 === */
.metric-card {
    background: linear-gradient(135deg, #1C2533 0%, #161B22 100%);
    border: 1px solid #30363D;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
    transition: all 0.3s;
}
.metric-card:hover {
    border-color: #00D4AA;
    box-shadow: 0 0 20px rgba(0,212,170,0.12);
}
.metric-value {
    font-size: 2.4rem;
    font-weight: 700;
    background: linear-gradient(135deg, #00D4AA, #00B4D8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.2;
}
.metric-label {
    font-size: 0.85rem;
    color: #8B949E;
    margin-top: 4px;
}
.metric-delta {
    font-size: 0.8rem;
    color: #00D4AA;
    margin-top: 2px;
}

/* === 渐变分割线 === */
.gradient-divider {
    height: 2px;
    background: linear-gradient(90deg, transparent, #00D4AA, transparent);
    margin: 10px 0 20px 0;
    border: none;
}

/* === 标题 === */
.main-title {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #E6EDF3 0%, #00D4AA 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
}
.sub-title {
    font-size: 0.9rem;
    color: #8B949E;
    margin-bottom: 8px;
}

/* === 场景按钮 === */
.scenario-btn {
    background: #1C2533;
    border: 1px solid #30363D;
    border-radius: 8px;
    padding: 10px 14px;
    color: #E6EDF3;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 0.85rem;
    margin-bottom: 6px;
    width: 100%;
}
.scenario-btn:hover {
    border-color: #00D4AA;
    background: #1F2A3A;
}

/* === Tab 样式 === */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: #0D1117;
    padding: 6px;
    border-radius: 10px;
    border: 1px solid #21262D;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 20px;
    color: #8B949E;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #00D4AA20, #00B4D820) !important;
    color: #00D4AA !important;
}

/* === 侧边栏 === */
[data-testid="stSidebar"] {
    background: #0D1117;
    border-right: 1px solid #21262D;
}

/* === 按钮 === */
.stButton > button {
    background: linear-gradient(135deg, #00D4AA, #00B4D8) !important;
    color: #0D1117 !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    font-size: 1rem !important;
    transition: all 0.3s !important;
    letter-spacing: 0.5px;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(0,212,170,0.3);
}

/* === 提示框 === */
.stAlert {
    border-radius: 10px;
    border: 1px solid #30363D;
}

/* === 对比容器（用于幻灯片效果）=== */
.comparison-container {
    position: relative;
    border-radius: 12px;
    overflow: hidden;
    border: 2px solid #30363D;
}

/* === 动画 === */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}
.auto-demo-indicator {
    animation: pulse 1.5s infinite;
    color: #00D4AA;
    font-weight: 600;
}

/* 数值弹出动画 */
@keyframes countUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.animate-in {
    animation: countUp 0.5s ease-out;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 会话状态
# ============================================================
def init_session():
    defaults = {
        "result": None, "mode": "energy", "last_params": None,
        "auto_demo_running": False, "auto_demo_idx": 0,
        "slider_position": 50,  # 对比滑块位置
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ============================================================
# 核心函数
# ============================================================
def run_sim(params, mode="energy"):
    t0 = time.time()
    if mode == "energy":
        result = run_energy_comparison(
            path_type=params["path_type"], laser_power=params["laser_power"],
            beam_radius=params["beam_radius"], scan_width=params["scan_width"],
            feed_rate=params["feed_rate"], n_pts=500, resolution=0.15e-3,
        )
    else:
        result = run_comparison_simulation(
            material_name=params["material_name"], path_type=params["path_type"],
            laser_power=params["laser_power"], beam_radius=params["beam_radius"],
            scan_width=params["scan_width"], feed_rate=params["feed_rate"],
        )
    return result, time.time() - t0


def compute_metrics(result, mode):
    """从结果中提取核心指标"""
    eb = result.get("energy_before")
    ea = result.get("energy_after")
    if eb is not None and ea is not None:
        h = eb.shape[0]
        cy, band = h // 2, h // 6
        b_e = (eb[cy-band-3:cy-band,:].mean() + eb[cy+band:cy+band+3,:].mean())/2
        b_c = eb[cy-3:cy+3,:].mean()
        a_e = (ea[cy-band-3:cy-band,:].mean() + ea[cy+band:cy+band+3,:].mean())/2
        a_c = ea[cy-3:cy+3,:].mean()
        ec_before = b_e / max(b_c, 1e-6)
        ec_after = a_e / max(a_c, 1e-6)
        uniformity_gain = ((ec_before - ec_after) / ec_before * 100) if ec_before > 0 else 0
        return {
            "uniformity": uniformity_gain,
            "ec_before": ec_before,
            "ec_after": ec_after,
            "power_range": result['power_stats']['power_range_ratio'],
            "power_min": result['power_stats']['optimized_min'],
            "power_max": result['power_stats']['optimized_max'],
            "density_before_std": result['trajectory_before']['density'].std(),
            "density_after_std": result['trajectory_after']['density'].std(),
        }
    # Thermal mode metrics
    std_r = result.get("std_reduction_pct", 0)
    return {
        "uniformity": std_r,
        "ec_before": 0, "ec_after": 0,
        "power_range": result['power_stats']['power_range_ratio'],
        "power_min": result['power_stats']['optimized_min'],
        "power_max": result['power_stats']['optimized_max'],
        "density_before_std": 0, "density_after_std": 0,
    }


# ============================================================
# 侧边栏
# ============================================================
def render_sidebar():
    st.sidebar.markdown("""
    <div style="text-align:center; padding:10px 0 0 0;">
        <div style="font-size:1.4rem; font-weight:700; color:#00D4AA;">智融光迹</div>
        <div style="font-size:0.75rem; color:#8B949E;">ZhiRongGuangJi v2.0</div>
    </div>
    <hr class='gradient-divider'>
    """, unsafe_allow_html=True)

    # === 预设场景 ===
    st.sidebar.markdown("### 预设 Demo 场景")
    scenario_names = get_demo_list()
    scenario_labels = [
        " 航空发动机涡轮叶片",
        " 飞机起落架曲面加工",
        " 陶瓷基复合材料加工",
        " 航天结构件宽幅扫描",
    ]

    selected_scenario = None
    for i, (name, label) in enumerate(zip(scenario_names, scenario_labels)):
        if st.sidebar.button(label, key=f"scenario_{i}", use_container_width=True,
                              help=DEMO_SCENARIOS[name]["description"]):
            selected_scenario = name

    st.sidebar.markdown("---")

    # === 仿真模式 ===
    mode_label = st.sidebar.radio(
        "仿真模式",
        [" 快速预览 (<0.1s)", " 完整热仿真 (2-5s)"],
        index=0,
    )
    mode = "energy" if "快速" in mode_label else "thermal"

    st.sidebar.markdown("---")

    # === 材料 ===
    mat_name = st.sidebar.selectbox("工件材料", list(MATERIALS.keys()), index=0)
    mat = MATERIALS[mat_name]
    st.sidebar.caption(f"k={mat['thermal_conductivity']} | cp={mat['specific_heat']} | {mat['density']}")

    st.sidebar.markdown("---")

    # === 激光参数 ===
    st.sidebar.markdown("#### 激光参数")
    c1, c2 = st.sidebar.columns(2)
    laser_power = c1.slider("功率 (W)", 100, 2000, 400, 50)
    beam_r_mm = c2.slider("光斑半径 (mm)", 0.5, 5.0, 1.0, 0.1)
    c3, c4 = st.sidebar.columns(2)
    scan_w_mm = c3.slider("扫描宽度 (mm)", 2, 30, 10, 1)
    feed_r_mm = c4.slider("进给速度 (mm/s)", 2, 50, 10, 1)

    st.sidebar.markdown("---")

    # === 路径 ===
    path_type = st.sidebar.selectbox("铣刀路径", ["直线", "正弦曲线", "S形曲线"], index=0)

    st.sidebar.markdown("---")

    # === 自动演示开关 ===
    st.sidebar.markdown("#### 答辩演示")
    auto_demo = st.sidebar.checkbox(" 自动循环演示", value=False,
                                     help="自动切换4个场景，每个展示8秒")

    st.sidebar.markdown("---")

    # === 运行按钮 ===
    run_btn = st.sidebar.button(" 运行仿真", type="primary", use_container_width=True)

    st.sidebar.markdown("---")
    st.sidebar.caption("同济大学 | 大学生创新大赛")

    return {
        "scenario": selected_scenario,
        "mode": mode,
        "material_name": mat_name,
        "laser_power": float(laser_power),
        "beam_radius": float(beam_r_mm) / 1000,
        "scan_width": float(scan_w_mm) / 1000,
        "feed_rate": float(feed_r_mm) / 1000,
        "path_type": path_type,
        "run_clicked": run_btn,
        "auto_demo": auto_demo,
    }


# ============================================================
# 指标卡片行
# ============================================================
def render_hero_metrics(metrics, elapsed):
    st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(f"""
        <div class="metric-card animate-in">
            <div class="metric-value">{metrics['uniformity']:.1f}%</div>
            <div class="metric-label">温度均匀性提升</div>
            <div class="metric-delta">▼ 边缘/中心比 {metrics['ec_before']:.2f} → {metrics['ec_after']:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        dens_reduce = ((metrics['density_before_std'] - metrics['density_after_std']) /
                        max(metrics['density_before_std'], 1e-6) * 100)
        st.markdown(f"""
        <div class="metric-card animate-in">
            <div class="metric-value">{abs(dens_reduce):.0f}%</div>
            <div class="metric-label">点密度方差降低</div>
            <div class="metric-delta">等弧长采样优化</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-card animate-in">
            <div class="metric-value">{metrics['power_range']:.1f}x</div>
            <div class="metric-label">功率动态调节范围</div>
            <div class="metric-delta">{metrics['power_min']:.0f} – {metrics['power_max']:.0f} W</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="metric-card animate-in">
            <div class="metric-value">{elapsed*1000:.0f}ms</div>
            <div class="metric-label">计算耗时</div>
            <div class="metric-delta">能量沉积快速预览</div>
        </div>
        """, unsafe_allow_html=True)

    with c5:
        st.markdown(f"""
        <div class="metric-card animate-in">
            <div class="metric-value">  </div>
            <div class="metric-label">效果评级</div>
            <div class="metric-delta">哑铃型 → 香肠型</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)


# ============================================================
# 对比滑块热力图（核心视觉亮点）
# ============================================================
def render_comparison_slider(result):
    """拖拽式对比滑块：左滑看优化前，右滑看优化后"""
    st.markdown("###  拖拽对比：优化前 vs 优化后")

    temp_b = result["temp_before"]
    temp_a = result["temp_after"]
    x_mm = result["x_mm"]
    y_mm = result["y_mm"]

    slider_pos = st.slider(
        "拖动滑块查看优化效果", 0, 100, 50, 1,
        label_visibility="collapsed",
        help="← 左滑看优化前（哑铃型） | 右滑看优化后（香肠型）→",
    )
    st.session_state["slider_position"] = slider_pos

    # 用两列模拟左右分屏
    left_col, right_col = st.columns([slider_pos, 100 - slider_pos])

    with left_col:
        st.markdown('<p style="color:#FF6B6B;font-weight:600;margin:0;"> 优化前 — 哑铃型</p>',
                     unsafe_allow_html=True)
        fig_b = plots_3d.plot_surface_heatmap(
            temp_b, x_mm, y_mm,
            title="",
            colorscale="Reds",
            zmin=min(temp_b.min(), temp_a.min()),
            zmax=max(temp_b.max(), temp_a.max()),
        )
        st.plotly_chart(fig_b, use_container_width=True,
                         config={'displayModeBar': False})

    with right_col:
        st.markdown('<p style="color:#4ECDC4;font-weight:600;margin:0;"> 优化后 — 香肠型</p>',
                     unsafe_allow_html=True)
        fig_a = plots_3d.plot_surface_heatmap(
            temp_a, x_mm, y_mm,
            title="",
            colorscale="Greens",
            zmin=min(temp_b.min(), temp_a.min()),
            zmax=max(temp_b.max(), temp_a.max()),
        )
        st.plotly_chart(fig_a, use_container_width=True,
                         config={'displayModeBar': False})


# ============================================================
# 自动演示引擎
# ============================================================
def auto_demo_runner():
    """自动循环演示：切换4个场景"""
    if not st.session_state.get("auto_demo_running", False):
        return

    scenarios = list(DEMO_SCENARIOS.values())
    idx = st.session_state.get("auto_demo_idx", 0)

    scenario = scenarios[idx]
    params = {
        "material_name": scenario["material_name"],
        "path_type": scenario["path_type"],
        "laser_power": scenario["laser_power"],
        "beam_radius": scenario["beam_radius"],
        "scan_width": scenario["scan_width"],
        "feed_rate": scenario["feed_rate"],
    }

    result, elapsed = run_sim(params, "energy")
    st.session_state["result"] = result
    st.session_state["last_params"] = params
    st.session_state["auto_demo_idx"] = (idx + 1) % len(scenarios)

    # 每8秒自动刷新
    time.sleep(8)
    st.rerun()


# ============================================================
# 主界面
# ============================================================
def render_main(result, mode, metrics, elapsed):
    # === 标题 ===
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:16px;">
        <div style="font-size:2.4rem;">  </div>
        <div>
            <div class="main-title">智融光迹控制软件</div>
            <div class="sub-title">基于神经网络的激光轨迹优化 | 三维温度场仿真与参数优化平台 | 同济大学</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # === 指标 ===
    render_hero_metrics(metrics, elapsed)

    # === 场景信息 ===
    params = st.session_state.get("last_params", {})
    if params:
        mat_name = params.get("material_name", "")
        path = params.get("path_type", "")
        power = params.get("laser_power", 0)
        scan_w = params.get("scan_width", 0) * 1000
        st.markdown(
            f" **当前场景**: {mat_name} | {path}路径 | {power:.0f}W | 扫描宽度 {scan_w:.0f}mm | "
            f"{'快速预览模式 (<0.1s)' if mode == 'energy' else '完整热仿真模式'}"
        )

    st.markdown("---")

    # === 核心亮点：对比滑块 ===
    if mode == "energy":
        render_comparison_slider(result)

    st.markdown("---")

    # === 统一键名：热仿真模式补充energy模式的键 ===
    if mode != "energy":
        grid = result["grid"]
        result["x_mm"] = np.linspace(0, (grid["nx"] - 1) * grid["dx"] * 1000, grid["nx"])
        result["y_mm"] = np.linspace(0, (grid["ny"] - 1) * grid["dy"] * 1000, grid["ny"])
        result["y_profile_before"] = result["surface_before"][grid["nx"] // 2, :]
        result["y_profile_after"] = result["surface_after"][grid["nx"] // 2, :]
        result["temp_before"] = result["surface_before"]
        result["temp_after"] = result["surface_after"]

    # === 四个Tab ===
    tab1, tab2, tab3, tab4 = st.tabs([
        "  轨迹优化", "  功率优化", "  温度场详细对比", "  3D 可视化",
    ])

    with tab1:
        st.markdown("### 激光扫描轨迹：传统 vs 等弧长采样")
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown('<p style="color:#FF6B6B;font-weight:600;"> 优化前 — 传统正弦振荡</p>',
                         unsafe_allow_html=True)
            st.caption("均匀时间采样 → 边缘密、中心疏")
            fig = plots_2d.plot_trajectory(
                result["trajectory_before"]["points"],
                title="",
            )
            st.plotly_chart(fig, use_container_width=True)
        with col_r:
            st.markdown('<p style="color:#4ECDC4;font-weight:600;"> 优化后 — 等弧长重采样</p>',
                         unsafe_allow_html=True)
            st.caption("弧长均等 → 点分布均匀")
            fig = plots_2d.plot_trajectory(
                result["trajectory_after"]["points"],
                title="",
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 点密度分布对比")
        fig = plots_2d.plot_point_density(
            result["trajectory_before"]["density"],
            result["trajectory_after"]["density"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("### PWM 功率实时补偿")
        c1, c2 = st.columns([3, 2])
        with c1:
            fig = plots_2d.plot_power_curve(
                result["power_constant"], result["power_optimized"],
            )
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            ps = result["power_stats"]
            st.markdown(f"""
            <div style="background:#1C2533;border:1px solid #30363D;border-radius:12px;padding:20px;margin-top:40px;">
                <h4 style="color:#00D4AA;margin-top:0;"> 功率参数</h4>
                <table style="width:100%;color:#E6EDF3;font-size:0.9rem;">
                <tr><td>基础功率</td><td style="text-align:right;font-weight:600;">{ps['base_power']:.0f} W</td></tr>
                <tr><td>优化均值</td><td style="text-align:right;font-weight:600;">{ps['optimized_mean']:.0f} W</td></tr>
                <tr><td>功率范围</td><td style="text-align:right;font-weight:600;color:#FF6B6B;">{ps['optimized_min']:.0f}</td></tr>
                <tr><td></td><td style="text-align:right;font-weight:600;color:#4ECDC4;">{ps['optimized_max']:.0f}</td></tr>
                <tr><td>调节幅度</td><td style="text-align:right;font-weight:600;">{ps['power_range_ratio']:.1f}x</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### Y 方向能量剖面：凹 → 平")
        fig = plots_2d.plot_y_temperature_profile(
            result["y_mm"], result["y_profile_before"], result["y_profile_after"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.markdown("### 表面温度场：并排对比")
        fig = plots_3d.plot_before_after_heatmaps(
            result["temp_before"], result["temp_after"],
            result["x_mm"], result["y_mm"],
        )
        st.plotly_chart(fig, use_container_width=True)

        show_optimization_summary(result, mode=mode)

    with tab4:
        st.markdown("### 三维温度场可视化")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<p style="color:#FF6B6B;font-weight:600;"> 优化前 — 双峰形态</p>',
                         unsafe_allow_html=True)
            fig = plots_3d.plot_3d_surface(
                result["temp_before"], result["x_mm"], result["y_mm"],
                title="",
                colorscale="Reds",
            )
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown('<p style="color:#4ECDC4;font-weight:600;"> 优化后 — 均匀平坦</p>',
                         unsafe_allow_html=True)
            fig = plots_3d.plot_3d_surface(
                result["temp_after"], result["x_mm"], result["y_mm"],
                title="",
                colorscale="Greens",
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        <div style="background:#1C2533;border:1px solid #30363D;border-radius:12px;padding:16px;margin-top:12px;">
            <span style="color:#00D4AA;"> </span>
            <strong>色阶说明：</strong>
            深红 = 高温 (>800°C) | 黄色 = 中温 (400-800°C) | 深蓝 = 低温 (<200°C)<br>
            <strong>优化前（哑铃型）：</strong>扫描带两侧能量集中，温度面呈"双峰"<br>
            <strong>优化后（香肠型）：</strong>功率补偿使温度在扫描带内均匀分布
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# 欢迎页
# ============================================================
def render_welcome():
    st.markdown("""
    <div style="text-align:center; padding:60px 20px;">
        <div style="font-size:3rem;"></div>
        <div class="main-title" style="font-size:2.8rem;">智融光迹</div>
        <div class="sub-title" style="font-size:1.1rem; margin-top:8px;">
            基于神经网络的激光轨迹优化技术<br>
            三维温度场仿真与加工参数优化平台
        </div>

        <div class="gradient-divider" style="margin:30px auto; width:60%;"></div>

        <div style="display:flex; justify-content:center; gap:40px; margin:30px 0; flex-wrap:wrap;">
            <div class="metric-card" style="min-width:140px;">
                <div class="metric-value">  </div>
                <div class="metric-label">等弧长采样</div>
            </div>
            <div class="metric-card" style="min-width:140px;">
                <div class="metric-value">  </div>
                <div class="metric-label">PWM功率补偿</div>
            </div>
            <div class="metric-card" style="min-width:140px;">
                <div class="metric-value">  </div>
                <div class="metric-label">动态角度因子</div>
            </div>
            <div class="metric-card" style="min-width:140px;">
                <div class="metric-value">  </div>
                <div class="metric-label">3D温度场仿真</div>
            </div>
        </div>

        <div style="color:#8B949E; font-size:0.9rem; margin-top:40px;">
             在左侧面板选择场景和参数<br>
             点击 <strong style="color:#00D4AA;">运行仿真</strong> 开始体验
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# 主入口
# ============================================================
def main():
    init_session()

    # 自动演示逻辑
    if st.session_state.get("auto_demo_running", False):
        auto_demo_runner()

    params = render_sidebar()

    # 自动演示开关
    st.session_state["auto_demo_running"] = params["auto_demo"]
    if params["auto_demo"] and not st.session_state.get("result"):
        st.session_state["auto_demo_idx"] = 0
        st.rerun()

    # 处理预设场景选择
    if params["scenario"]:
        sc = DEMO_SCENARIOS[params["scenario"]]
        params["material_name"] = sc["material_name"]
        params["path_type"] = sc["path_type"]
        params["laser_power"] = sc["laser_power"]
        params["beam_radius"] = sc["beam_radius"]
        params["scan_width"] = sc["scan_width"]
        params["feed_rate"] = sc["feed_rate"]
        # 触发运行
        mode = params["mode"]
        result, elapsed = run_sim(params, mode)
        st.session_state["result"] = result
        st.session_state["last_params"] = params
        metrics = compute_metrics(result, mode)
        render_main(result, mode, metrics, elapsed)
        return

    # 手动运行
    if params["run_clicked"]:
        mode = params["mode"]
        result, elapsed = run_sim(params, mode)
        st.session_state["result"] = result
        st.session_state["last_params"] = params
        metrics = compute_metrics(result, mode)
        render_main(result, mode, metrics, elapsed)
        return

    # 已有结果则保持显示
    if st.session_state.get("result") is not None:
        mode = st.session_state.get("mode", "energy")
        result = st.session_state["result"]
        elapsed = 0.08  # 近似值
        metrics = compute_metrics(result, mode)
        render_main(result, mode, metrics, elapsed)
    else:
        render_welcome()


if __name__ == "__main__":
    main()
