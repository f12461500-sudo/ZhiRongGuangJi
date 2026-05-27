# 智融光迹 ZhiRongGuangJi

> **基于神经网络的激光轨迹优化技术** — 三维温度场仿真与加工参数优化平台

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 项目简介

**智融光迹**是一款面向激光辅助加工（LAMill）的智能控制软件原型。针对航空航天领域中镍基/钛基超合金、陶瓷基复合材料等"难加工材料"的制造瓶颈，本软件通过**等弧长采样**、**动态角度因子**和**PWM功率补偿**三大核心技术，将传统加工的"哑铃型"非均匀温度场优化为均匀的"香肠型"温度场。

### 核心创新

| 技术 | 解决的问题 | 效果 |
|------|-----------|------|
| **等弧长采样均匀化** | 正弦振荡导致轨迹点密度不均 | 弧长方差 ↓76% |
| **动态角度因子算法** | 铣刀转弯处轨迹交叠、局部过热 | 复杂曲面均匀性 ↑34.9% |
| **PWM功率实时补偿** | 固定功率无法适应密度变化 | 冷区加功率、热区降功率 |
| **双模式仿真架构** | 参数探索慢 vs 仿真精度需求 | 快速预览 <0.1s / 精确仿真 2-5s |

### 效果展示

```
优化前（哑铃型）:  ██░░░░░░██    边缘热、中心冷
优化后（香肠型）:  ██████████    温度均匀分布
均匀性提升: 17% ~ 78%（因场景而异）
```

---

## 快速开始

### 在线体验（推荐）

> 部署到 Streamlit Cloud 后，将链接放在这里：
> **[🔗 在线体验地址](https://your-app-name.streamlit.app)**

### 本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/ZhiRongGuangJi.git
cd ZhiRongGuangJi

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动应用
streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`

---

## 使用指南

### 1. 选择场景（侧边栏）

软件预置了 **4 个典型工业场景**，一键加载参数：

| 场景 | 材料 | 路径 | 特点 |
|------|------|------|------|
| 航空发动机涡轮叶片 | TC4 钛合金 | 直线 | 最典型的哑铃→香肠转变 |
| 飞机起落架曲面加工 | Inconel 718 | S 形曲线 | 动态角度因子效果最显著 |
| 陶瓷基复合材料加工 | Al₂O₃ | 正弦曲线 | 低导热材料，优化效果极佳 |
| 航天结构件精密加工 | TC4 钛合金 | 直线（宽幅）| 宽幅扫描场景 |

也可以**自定义参数**：材料、激光功率、光斑半径、扫描宽度、进给速度、路径类型。

### 2. 两种仿真模式

- **快速预览（能量沉积）**：< 0.1 秒出结果，适合快速探索参数
- **完整热仿真（有限差分）**：2-5 秒，3D 有限差分求解器精确计算

### 3. 四个可视化标签页

| 标签 | 内容 | 答辩亮点 |
|------|------|----------|
| **轨迹优化** | 优化前/后 2D 轨迹 + 点密度分布 | 弧长方差 ↓76% |
| **功率优化** | PWM 功率曲线 + Y 方向能量剖面 | 冷区加功率、热区降功率 |
| **温度场对比** | 并排热力图 + 优化效果分析 | **哑铃型 → 香肠型** |
| **3D 可视化** | 3D 温度场 surface + 时间演化 | 三维"双峰→平坦"形态变化 |

---

## 项目结构

```
ZhiRongGuangJi/
├── app.py                          # Streamlit 主界面
├── requirements.txt                # Python 依赖
├── core/
│   ├── config.py                   # 材料库、物理常量、默认参数
│   ├── thermal_model.py            # 3D 有限差分热传导求解器
│   ├── trajectory.py               # 轨迹生成：等弧长采样 + 动态角度因子
│   ├── power_optimizer.py          # PWM 功率补偿 + 神经网络代理模型
│   ├── energy_deposition.py        # 能量沉积快速预览模型
│   └── simulation_pipeline.py      # 完整仿真管线
├── visualization/
│   ├── plots_2d.py                 # 2D 图表：轨迹、功率、温度剖面
│   ├── plots_3d.py                 # 3D 热力图、surface、时间演化
│   └── comparison.py               # 优化前后对比视图
├── data/
│   └── demo_scenarios.py           # 4 个预设工业场景
└── docs/
    ├── 答辩使用指南-抓住评委眼睛.md
    └── 本科生工作贡献说明.md
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Streamlit |
| 可视化 | Plotly (2D/3D charts, heatmap, surface) |
| 数值计算 | NumPy, SciPy |
| 物理模型 | 3D 显式有限差分法 (FDM) |
| 热源模型 | 移动高斯表面热流 |
| 轨迹算法 | 等弧长重采样、曲率自适应角度因子 |

---

## 技术原理

### 逆向思维：从温度场到激光参数

传统方法是"正向"计算——给定激光参数，求解温度场。本项目的创新在于**反向推导**：

```
目标温度场（均匀）──→ 神经网络 ──→ 最优激光功率曲线
                   ──→ 等弧长采样 ──→ 均匀扫描轨迹
```

### 核心算法

**1. 等弧长采样**
```
密集生成轨迹 → 计算累积弧长 → 等间距重采样 → 均匀点分布
```

**2. 动态角度因子**
```
angle_factor = 1 + base_factor × |κ|^sharpness_factor
A_adjusted = A / angle_factor
```
在铣刀转弯处（曲率 κ 大），自动减弱激光振荡振幅，防止轨迹交叠。

**3. PWM 功率补偿**
```
P_i = base_power / density_i  （归一化后）
```
轨迹点密度高处自动降功率，密度低处自动升功率。

---

## 部署到 Streamlit Cloud

### 步骤 1：推送到 GitHub

```bash
cd ZhiRongGuangJi
git init
git add .
git commit -m "Initial commit: 智融光迹控制软件 v1.0"
git branch -M main
git remote add origin https://github.com/你的用户名/ZhiRongGuangJi.git
git push -u origin main
```

### 步骤 2：在 Streamlit Cloud 部署

1. 打开 [share.streamlit.io](https://share.streamlit.io)
2. 用 GitHub 账号登录
3. 点击 **"New app"**
4. 选择仓库 `你的用户名/ZhiRongGuangJi`
5. Branch: `main`
6. Main file path: `app.py`
7. 点击 **"Deploy!"**

等待 2-3 分钟，你会得到一个 `https://你的应用名.streamlit.app` 的永久链接。

### 步骤 3：更新 README 中的链接

部署成功后，把 README 中的在线体验链接替换为你的实际地址。

---

## 贡献者

| 姓名 | 角色 | 学院 |
|------|------|------|
| 刘冠辰 | 项目总负责人 | 机械工程与机器人学院 |
| 李佳诺 | 算法开发 | — |
| 杨国健 | 系统集成 | 电子与信息工程学院 |
| 沈子富 | 前端开发 | 计算机科学与技术学院 |
| 李锦涛 | 商业分析 | 计算机科学与技术学院 |

**指导教师**：徐东东教授（同济大学）

---

## 参赛信息

- **赛事**：大学生创新大赛
- **项目类型**：科技创新类
- **所属高校**：同济大学

---

## License

MIT License — 详见 [LICENSE](LICENSE) 文件

---

*Made with ❤️ by 同济大学智融光迹团队 | 2026*
