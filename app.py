"""智融光迹控制软件 - 主界面

基于神经网络的激光轨迹优化技术
三维温度场仿真与加工参数优化平台
"""

import streamlit as st
import numpy as np
import time

# 页面配置
st.set_page_config(
    page_title="智融光迹控制软件",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 导入核心模块
from core.config import MATERIALS, DEFAULT_LASER, DEFAULT_GRID
from core.energy_deposition import run_energy_comparison
from core.simulation_pipeline import run_comparison_simulation
from visualization import plots_2d, plots_3d
from visualization.comparison import show_metrics_cards, show_optimization_summary
from data.demo_scenarios import DEMO_SCENARIOS, get_demo_list

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        font-weight: bold;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化会话状态"""
    defaults = {
        "result": None,
        "mode": "energy",  # "energy" | "thermal"
        "sim_running": False,
        "last_params": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render_sidebar():
    """渲染侧边栏参数面板"""
    st.sidebar.title("控制面板")

    # === 预设Demo场景 (放在最前面) ===
    st.sidebar.subheader("预设Demo场景")
    demo_name = st.sidebar.selectbox(
        "快速加载典型场景",
        options=["(自定义参数)"] + get_demo_list(),
        index=0,
        help="选择预置场景自动填充参数，也可在此基础上微调",
    )

    # 获取Demo参数作为默认值
    if demo_name != "(自定义参数)":
        demo = DEMO_SCENARIOS[demo_name]
        default_mat_name = demo["material_name"]
        default_mat_idx = list(MATERIALS.keys()).index(demo["material_name"])
        default_power = demo["laser_power"]
        default_beam = demo["beam_radius"] * 1000
        default_scan = demo["scan_width"] * 1000
        default_feed = demo["feed_rate"] * 1000
        default_path = demo["path_type"]
        with st.sidebar.expander("场景说明", expanded=False):
            st.caption(demo["description"])
    else:
        default_mat_name = list(MATERIALS.keys())[0]
        default_mat_idx = 0
        default_power = DEFAULT_LASER["power"]
        default_beam = DEFAULT_LASER["beam_radius"] * 1000
        default_scan = DEFAULT_LASER["scan_width"] * 1000
        default_feed = DEFAULT_LASER["feed_rate"] * 1000
        default_path = "直线"

    st.sidebar.markdown("---")

    # 模式选择
    mode = st.sidebar.radio(
        "仿真模式",
        options=["快速预览 (能量沉积)", "完整热仿真 (FDM)"],
        help="快速预览: <1秒出结果\n完整仿真: 有限差分求解器,约2-5秒",
    )
    st.session_state["mode"] = "energy" if "快速" in mode else "thermal"

    st.sidebar.markdown("---")

    # 材料选择
    material_name = st.sidebar.selectbox(
        "工件材料",
        options=list(MATERIALS.keys()),
        index=default_mat_idx,
    )
    mat = MATERIALS[material_name]
    st.sidebar.caption(
        f"k={mat['thermal_conductivity']} W/(m·K) | "
        f"ρ={mat['density']} kg/m³ | "
        f"cp={mat['specific_heat']} J/(kg·K)"
    )

    st.sidebar.markdown("---")

    # 激光参数 (默认值来自Demo选择)
    st.sidebar.subheader("激光参数")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        laser_power = st.number_input(
            "功率 (W)", min_value=100, max_value=2000,
            value=int(default_power), step=50,
        )
    with col2:
        beam_radius = st.number_input(
            "光斑半径 (mm)", min_value=0.5, max_value=5.0,
            value=float(default_beam), step=0.1,
        ) / 1000.0

    col3, col4 = st.sidebar.columns(2)
    with col3:
        scan_width = st.number_input(
            "扫描宽度 (mm)", min_value=2.0, max_value=30.0,
            value=float(default_scan), step=1.0,
        ) / 1000.0
    with col4:
        feed_rate = st.number_input(
            "进给速度 (mm/s)", min_value=2.0, max_value=50.0,
            value=float(default_feed), step=1.0,
        ) / 1000.0

    st.sidebar.markdown("---")

    # 轨迹参数
    st.sidebar.subheader("铣刀轨迹")
    path_idx = ["直线", "正弦曲线", "S形曲线"].index(default_path)
    path_type = st.sidebar.selectbox(
        "路径类型",
        options=["直线", "正弦曲线", "S形曲线"],
        index=path_idx,
    )

    st.sidebar.markdown("---")

    # 运行按钮
    run_clicked = st.button(
        "运行仿真",
        type="primary",
        use_container_width=True,
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("智融光迹 v1.0 | 同济大学")
    st.sidebar.caption("基于神经网络的激光轨迹优化技术")

    return {
        "material_name": material_name,
        "laser_power": float(laser_power),
        "beam_radius": float(beam_radius),
        "scan_width": float(scan_width),
        "feed_rate": float(feed_rate),
        "path_type": path_type,
        "run_clicked": run_clicked,
        "demo_name": demo_name,
    }


def run_simulation(params):
    """执行仿真"""
    with st.spinner("仿真计算中..."):
        t0 = time.time()

        if st.session_state["mode"] == "energy":
            result = run_energy_comparison(
                path_type=params["path_type"],
                laser_power=params["laser_power"],
                beam_radius=params["beam_radius"],
                scan_width=params["scan_width"],
                feed_rate=params["feed_rate"],
                n_pts=500,
                resolution=0.15e-3,
            )
        else:
            result = run_comparison_simulation(
                material_name=params["material_name"],
                path_type=params["path_type"],
                laser_power=params["laser_power"],
                beam_radius=params["beam_radius"],
                scan_width=params["scan_width"],
                feed_rate=params["feed_rate"],
            )

        elapsed = time.time() - t0
        st.session_state["result"] = result
        st.session_state["last_params"] = params

    st.toast(f"仿真完成! 耗时 {elapsed:.1f}s")


def render_main_ui(result, mode):
    """渲染主界面内容"""
    st.title("智融光迹控制软件")
    st.caption("基于神经网络的激光轨迹优化 | 三维温度场仿真与加工参数优化")

    st.markdown("---")

    # 指标卡片
    if mode == "energy":
        # Energy mode metrics
        eb = result["energy_before"]
        ea = result["energy_after"]
        h = eb.shape[0]
        cy = h // 2
        band = h // 6
        b_edge = (eb[cy - band - 3:cy - band, :].mean() +
                   eb[cy + band:cy + band + 3, :].mean()) / 2
        b_center = eb[cy - 3:cy + 3, :].mean()
        a_edge = (ea[cy - band - 3:cy - band, :].mean() +
                   ea[cy + band:cy + band + 3, :].mean()) / 2
        a_center = ea[cy - 3:cy + 3, :].mean()

        edge_center_before = b_edge / max(b_center, 1e-6)
        edge_center_after = a_edge / max(a_center, 1e-6)
        uniformity_improve = ((edge_center_before - edge_center_after) /
                               edge_center_before * 100) if edge_center_before > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("均匀性提升", f"{uniformity_improve:.1f}%")
        with col2:
            st.metric("边缘/中心比 (前)", f"{edge_center_before:.3f}",
                       delta=f"{edge_center_before - edge_center_after:.3f}",
                       delta_color="inverse")
        with col3:
            st.metric("功率调节范围", f"{result['power_stats']['power_range_ratio']:.1f}x")
        with col4:
            st.metric("计算耗时", f"< 0.1s")
    else:
        # Thermal mode metrics
        std_r = result["std_reduction_pct"]
        max_r = result["max_diff_reduction_pct"]
        ps = result["power_stats"]
        sb = result["temp_stats_before"][-1]
        sa = result["temp_stats_after"][-1]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("温度标准差降低", f"{std_r:.1f}%")
        with col2:
            st.metric("最高温差降低", f"{max_r:.1f}%")
        with col3:
            st.metric("峰值温度", f"{sa['max']:.0f}°C",
                       delta=f"{sa['max'] - sb['max']:.0f}°C")
        with col4:
            st.metric("功率范围", f"{ps['power_range_ratio']:.1f}x")

    st.markdown("---")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "轨迹优化", "功率优化", "温度场对比", "3D可视化"
    ])

    # === Tab 1: 轨迹优化 ===
    with tab1:
        st.subheader("激光扫描轨迹优化")

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("**优化前: 传统正弦振荡**")
            st.markdown("点分布不均 → 边缘密集、中心稀疏 → 能量不均匀")
            fig_traj_b = plots_2d.plot_trajectory(
                result["trajectory_before"]["points"],
                title="优化前轨迹 (传统采样)",
            )
            st.plotly_chart(fig_traj_b, use_container_width=True)

        with col_r:
            st.markdown("**优化后: 等弧长采样 + 动态角度因子**")
            st.markdown("点分布均匀 → 弧长均等 → 能量均匀输入")
            fig_traj_a = plots_2d.plot_trajectory(
                result["trajectory_after"]["points"],
                title="优化后轨迹 (等弧长采样)",
            )
            st.plotly_chart(fig_traj_a, use_container_width=True)

        # 点密度对比
        st.markdown("### 点密度分布对比")
        fig_density = plots_2d.plot_point_density(
            result["trajectory_before"]["density"],
            result["trajectory_after"]["density"],
        )
        st.plotly_chart(fig_density, use_container_width=True)

    # === Tab 2: 功率优化 ===
    with tab2:
        st.subheader("激光功率实时补偿")

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("**优化前: 恒定功率**")
            st.markdown("全程固定功率，高密度区能量过剩，低密度区能量不足")
            fig_pow = plots_2d.plot_power_curve(
                result["power_constant"],
                result["power_optimized"],
            )
            st.plotly_chart(fig_pow, use_container_width=True)

        with col_r:
            st.markdown("**优化后: 密度补偿功率**")
            st.markdown("实时调节 → 冷区加功率、热区降功率 → 能量均匀")
            ps = result["power_stats"]
            st.markdown(f"""
            | 参数 | 值 |
            |------|-----|
            | 基础功率 | {ps['base_power']:.0f} W |
            | 优化后均值 | {ps['optimized_mean']:.0f} W |
            | 功率范围 | [{ps['optimized_min']:.0f}, {ps['optimized_max']:.0f}] W |
            | 调节幅度 | {ps['power_range_ratio']:.1f}x |
            """)

        # Y方向温度/能量剖面
        st.markdown("### 能量/温度剖面 (Y方向中心截面)")
        if mode == "energy":
            fig_yp = plots_2d.plot_y_temperature_profile(
                result["y_mm"],
                result["y_profile_before"],
                result["y_profile_after"],
            )
        else:
            fig_yp = plots_2d.plot_y_temperature_profile(
                result["y_mm"],
                result["y_profile_before"],
                result["y_profile_after"],
            )
        st.plotly_chart(fig_yp, use_container_width=True)

    # === Tab 3: 温度场对比 ===
    with tab3:
        st.subheader("温度场对比: 哑铃型 → 香肠型")

        if mode == "energy":
            # 能量沉积模式 - 使用合成温度
            fig_comp = plots_3d.plot_before_after_heatmaps(
                result["temp_before"],
                result["temp_after"],
                result["x_mm"],
                result["y_mm"],
            )
            st.plotly_chart(fig_comp, use_container_width=True)

            show_optimization_summary(result, mode="energy")
        else:
            # 完整热仿真模式
            fig_comp = plots_3d.plot_before_after_heatmaps(
                result["surface_before"],
                result["surface_after"],
                np.linspace(0, (result["grid"]["nx"] - 1) * result["grid"]["dx"] * 1000,
                            result["grid"]["nx"]),
                np.linspace(0, (result["grid"]["ny"] - 1) * result["grid"]["dy"] * 1000,
                            result["grid"]["ny"]),
            )
            st.plotly_chart(fig_comp, use_container_width=True)

            show_optimization_summary(result, mode="thermal")

            # 时间演化
            st.markdown("### 温度场时间演化 (优化后)")
            fig_evol = plots_3d.plot_temperature_evolution(
                result["snapshots_after"],
                result["times_after"],
                np.linspace(0, (result["grid"]["nx"] - 1) * result["grid"]["dx"] * 1000,
                            result["grid"]["nx"]),
                np.linspace(0, (result["grid"]["ny"] - 1) * result["grid"]["dy"] * 1000,
                            result["grid"]["ny"]),
            )
            st.plotly_chart(fig_evol, use_container_width=True)

    # === Tab 4: 3D可视化 ===
    with tab4:
        st.subheader("三维温度场可视化")

        if mode == "energy":
            col_l, col_r = st.columns(2)
            with col_l:
                fig_3d_b = plots_3d.plot_3d_surface(
                    result["temp_before"],
                    result["x_mm"],
                    result["y_mm"],
                    title="优化前 3D温度场 (哑铃型)",
                )
                st.plotly_chart(fig_3d_b, use_container_width=True)
            with col_r:
                fig_3d_a = plots_3d.plot_3d_surface(
                    result["temp_after"],
                    result["x_mm"],
                    result["y_mm"],
                    title="优化后 3D温度场 (香肠型)",
                )
                st.plotly_chart(fig_3d_a, use_container_width=True)
        else:
            # Thermal mode 3D
            col_l, col_r = st.columns(2)
            with col_l:
                fig_3d_b = plots_3d.plot_3d_surface(
                    result["surface_before"],
                    np.linspace(0, (result["grid"]["nx"] - 1) * result["grid"]["dx"] * 1000,
                                result["grid"]["nx"]),
                    np.linspace(0, (result["grid"]["ny"] - 1) * result["grid"]["dy"] * 1000,
                                result["grid"]["ny"]),
                    title="优化前 3D温度场",
                )
                st.plotly_chart(fig_3d_b, use_container_width=True)
            with col_r:
                fig_3d_a = plots_3d.plot_3d_surface(
                    result["surface_after"],
                    np.linspace(0, (result["grid"]["nx"] - 1) * result["grid"]["dx"] * 1000,
                                result["grid"]["nx"]),
                    np.linspace(0, (result["grid"]["ny"] - 1) * result["grid"]["dy"] * 1000,
                                result["grid"]["ny"]),
                    title="优化后 3D温度场",
                )
                st.plotly_chart(fig_3d_a, use_container_width=True)

        st.markdown("""
        **色阶说明**: 深红=高温区 (>800°C), 黄色=中温区 (400-800°C), 蓝色=低温区 (<200°C)

        优化前的"哑铃型"分布：扫描带两侧能量集中形成高温，中间区域温度不足。
        优化后的"香肠型"分布：通过功率补偿实现扫描带内温度均匀化。
        """)


def main():
    """主函数"""
    init_session_state()
    params = render_sidebar()

    # 运行仿真
    if params["run_clicked"]:
        run_simulation(params)

    # 显示结果
    if st.session_state.get("result") is not None:
        render_main_ui(st.session_state["result"], st.session_state["mode"])
    else:
        # 初始状态 - 显示欢迎页
        st.title("智融光迹控制软件")
        st.markdown("""
        ### 基于神经网络的激光轨迹优化技术

        本软件演示激光辅助加工 (LAMill) 中，通过**智能轨迹优化**和**功率实时补偿**，
        将传统加工的"哑铃型"非均匀温度场，优化为均匀的"香肠型"温度场。

        ---

        #### 快速开始
        1. 在左侧面板选择材料和激光参数
        2. 点击 **运行仿真** 按钮
        3. 查看各标签页的对比结果

        #### 核心技术
        - **等弧长采样**: 消除正弦振荡带来的点密度不均
        - **动态角度因子**: 铣刀转弯处自动减弱振幅，防止轨迹交叠
        - **PWM功率补偿**: 根据轨迹点密度实时调节激光功率
        - **神经网络引擎**: 从目标温度场反向推导最优激光参数

        #### 仿真模式
        | 模式 | 速度 | 说明 |
        |------|------|------|
        | 快速预览 | <0.1s | 能量沉积模型，快速探索参数 |
        | 完整热仿真 | 2-5s | 3D有限差分求解器，精确热传导计算 |
        """)


if __name__ == "__main__":
    main()
