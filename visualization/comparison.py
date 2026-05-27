"""对比视图 - 优化前后指标卡片和汇总展示"""

import streamlit as st
import numpy as np


def show_metrics_cards(std_reduction, max_reduction, power_stats, temp_stats_before, temp_stats_after):
    """显示优化指标卡片"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="温度标准差降低",
            value=f"{std_reduction:.1f}%",
            delta=f"{std_reduction:.1f}%" if std_reduction > 0 else None,
        )
    with col2:
        st.metric(
            label="最高温差降低",
            value=f"{max_reduction:.1f}%",
            delta=f"{max_reduction:.1f}%" if max_reduction > 0 else None,
        )
    with col3:
        before_max = temp_stats_before[-1]["max"]
        after_max = temp_stats_after[-1]["max"]
        st.metric(
            label="峰值温度",
            value=f"{after_max:.0f}°C",
            delta=f"{after_max - before_max:.0f}°C",
        )
    with col4:
        st.metric(
            label="功率调节范围",
            value=f"{power_stats['power_range_ratio']:.1f}x",
            delta=f"[{power_stats['optimized_min']:.0f}-{power_stats['optimized_max']:.0f}]W",
        )


def show_optimization_summary(result, mode="energy"):
    """显示优化效果总结

    Args:
        result: simulation result dict
        mode: "energy" or "thermal"
    """
    st.markdown("### 优化效果总结")

    if mode == "energy":
        eb = result["energy_before"]
        ea = result["energy_after"]

        # Scan band analysis
        h = eb.shape[0]
        cy = h // 2
        band = h // 6
        b_edge = (eb[cy - band - 3:cy - band, :].mean() +
                   eb[cy + band:cy + band + 3, :].mean()) / 2
        b_center = eb[cy - 3:cy + 3, :].mean()
        a_edge = (ea[cy - band - 3:cy - band, :].mean() +
                   ea[cy + band:cy + band + 3, :].mean()) / 2
        a_center = ea[cy - 3:cy + 3, :].mean()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**优化前 (传统扫描)**")
            st.markdown(f"- 扫描带边缘/中心能量比: **{b_edge / b_center:.2f}**")
            st.markdown(f"- 能量分布标准差: **{eb.std():.1f}**")
            st.markdown(f"- 现象: 边缘能量集中 → **哑铃型**温度场")

        with col2:
            st.markdown("**优化后 (智能补偿)**")
            st.markdown(f"- 扫描带边缘/中心能量比: **{a_edge / a_center:.2f}**")
            st.markdown(f"- 能量分布标准差: **{ea.std():.1f}**")
            st.markdown(f"- 现象: 能量均匀分布 → **香肠型**温度场")

        improvement = (b_edge / b_center - a_edge / a_center) / (b_edge / b_center) * 100
        st.success(
            f"均匀性提升: **{improvement:.1f}%** | "
            f"边缘/中心比从 {b_edge / b_center:.2f} 降至 {a_edge / a_center:.2f}"
        )
    else:
        std_b = result["temp_stats_before"][-1]["std"]
        std_a = result["temp_stats_after"][-1]["std"]
        max_b = result["temp_stats_before"][-1]["max"]
        max_a = result["temp_stats_after"][-1]["max"]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**优化前 (恒功率)**")
            st.markdown(f"- 温度标准差: **{std_b:.1f}°C**")
            st.markdown(f"- 峰值温度: **{max_b:.0f}°C**")
        with col2:
            st.markdown("**优化后 (功率补偿)**")
            st.markdown(f"- 温度标准差: **{std_a:.1f}°C**")
            st.markdown(f"- 峰值温度: **{max_a:.0f}°C**")
