"""
智能简历推荐系统 —— 完整版
功能：支持默认6行业 + 用户自定义行业
公式：Score_i = Σ w_j · x_ij
运行：streamlit run shaixuanxitong.py
"""

import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib
from core import parse_resume, calculate_scores

# ============ 中文字体设置 ============
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False

# ============ 页面配置 ============
st.set_page_config(
    page_title="智能简历推荐系统",
    page_icon="📄",
    layout="wide"
)

st.title("📄 智能简历推荐系统")
st.markdown("基于熵权法多指标评价模型 · 支持自定义行业与权重")


# ============ 加载/管理权重 ============
@st.cache_data
def load_weights():
    """加载权重数据，优先从Excel读取"""
    if os.path.exists("weights.xlsx"):
        try:
            df = pd.read_excel("weights.xlsx", index_col=0)
            # 确保列名正确
            expected_cols = ['教育水平', '专业对口度', '公司实力', '稳定性', '晋升速度', '重大成果', '领导力']
            if all(col in df.columns for col in expected_cols):
                return df
        except:
            pass

    # 默认权重（对应论文表2）
    data = {
        '教育水平': [10.35, 27.78, 5.59, 6.83, 31.23, 0.00],
        '专业对口度': [16.62, 27.28, 8.82, 3.67, 1.09, 3.15],
        '公司实力': [10.86, 11.95, 6.86, 7.04, 2.76, 0.24],
        '稳定性': [12.47, 6.78, 10.72, 12.04, 0.27, 5.41],
        '晋升速度': [9.27, 4.97, 14.63, 13.94, 12.17, 0.00],
        '重大成果': [28.77, 11.15, 29.05, 24.83, 29.17, 54.92],
        '领导力': [11.67, 10.09, 24.33, 31.69, 23.31, 36.28]
    }
    industries = ['电商', '品牌', '人力资源', '生产', '销售', '研发']
    return pd.DataFrame(data, index=industries)


def save_weights(df):
    """保存权重到Excel"""
    try:
        df.to_excel("weights.xlsx")
        return True
    except:
        return False


# 加载权重
weights_df = load_weights()
industries = weights_df.index.tolist()

# ============ 侧边栏 ============
with st.sidebar:
    st.header("⚙️ 参数设置")

    # ---- 行业选择 ----
    industry = st.selectbox(
        "选择目标行业",
        industries,
        help="不同行业使用不同的权重配置"
    )

    # ---- 文件上传 ----
    st.divider()
    st.subheader("📤 上传简历")
    uploaded_files = st.file_uploader(
        "支持 .docx 格式（可多选）",
        type=['docx'],
        accept_multiple_files=True
    )

    # ---- 显示当前权重 ----
    with st.expander("📊 当前行业权重"):
        w_display = weights_df.loc[industry].to_frame().T
        st.dataframe(w_display.style.format("{:.2f}%"))

    st.caption("💡 上传后系统自动解析并排序")

    # ===== 新增：自定义行业功能 =====
    st.divider()
    st.subheader("➕ 新增自定义行业")

    with st.expander("点击展开，添加新行业"):
        new_industry = st.text_input(
            "行业名称",
            placeholder="例如：金融、医疗、教育...",
            key="new_industry_name"
        )

        st.caption("请为以下七个指标分配权重（总和应为100）")
        cols_new = st.columns(7)
        new_weights = []
        for i, (col, ind) in enumerate(zip(cols_new, weights_df.columns)):
            with col:
                w = st.number_input(
                    ind,
                    min_value=0.0,
                    max_value=100.0,
                    value=14.0,
                    step=1.0,
                    key=f"new_{ind}"
                )
                new_weights.append(w)

        # 显示权重总和
        total_new = sum(new_weights)
        if abs(total_new - 100) > 1:
            st.caption(f"⚠️ 当前总和：{total_new:.1f}（建议调整为100）")
        else:
            st.caption(f"✅ 总和：{total_new:.1f}")

        if st.button("✅ 添加行业", use_container_width=True):
            if not new_industry:
                st.warning("请输入行业名称！")
            elif new_industry in weights_df.index:
                st.warning(f"行业「{new_industry}」已存在！")
            else:
                total = sum(new_weights)
                if total == 0:
                    st.error("权重总和不能为0！")
                else:
                    # 归一化权重
                    norm_w = [w / total * 100 for w in new_weights]
                    weights_df.loc[new_industry] = norm_w
                    save_weights(weights_df)
                    st.success(f"✅ 行业「{new_industry}」已添加！请重新选择行业。")
                    st.rerun()

    # ---- 显示已支持的行业列表 ----
    with st.expander("📋 当前支持的行业"):
        st.write(", ".join(weights_df.index.tolist()))

# ============ 主区域 ============
if uploaded_files:
    st.subheader(f"📊 {industry}行业候选人排名")

    # ---- 解析简历 ----
    candidates = []
    progress_bar = st.progress(0)

    for i, file in enumerate(uploaded_files):
        try:
            import docx

            doc = docx.Document(file)
            text = '\n'.join([p.text for p in doc.paragraphs])
            cand = parse_resume(text, industry)
            cand['name'] = file.name.replace('.docx', '').replace('.DOCX', '')
            candidates.append(cand)
        except Exception as e:
            st.warning(f"⚠️ 解析失败：{file.name}")
        progress_bar.progress((i + 1) / len(uploaded_files))
    progress_bar.empty()

    if not candidates:
        st.warning("没有成功解析任何简历，请检查文件格式")
        st.stop()

    # ---- 计算得分 ----
    results = calculate_scores(candidates, industry, weights_df)

    # ---- 排名表 ----
    df_rank = pd.DataFrame([{
        '排名': i + 1,
        '候选人': r['name'],
        '综合得分': r['score']
    } for i, r in enumerate(results)])

    st.dataframe(
        df_rank.style.background_gradient(subset=['综合得分'], cmap='RdYlGn_r'),
        use_container_width=True,
        hide_index=True
    )

    # ---- 详情查看 ----
    st.divider()
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📋 候选人详情")
        selected_idx = st.selectbox(
            "选择查看详情",
            range(len(results)),
            format_func=lambda i: f"{i + 1}. {results[i]['name']}（得分：{results[i]['score']:.4f}）"
        )
        cand = results[selected_idx]
        st.metric("综合得分", f"{cand['score']:.4f}")

        detail_df = pd.DataFrame({
            '指标': list(cand['details'].keys()),
            '得分': list(cand['details'].values())
        })
        st.dataframe(detail_df, hide_index=True)

    with col2:
        st.subheader("🎯 能力画像")

        fig, ax = plt.subplots(figsize=(8, 5))

        names = list(cand['details'].keys())
        values = list(cand['details'].values())

        # 颜色：>=0.6绿色，>=0.4橙色，<0.4红色
        colors = ['#2ecc71' if v >= 0.6 else '#f39c12' if v >= 0.4 else '#e74c3c' for v in values]

        bars = ax.barh(names, values, color=colors, height=0.6, edgecolor='white', linewidth=1)

        for bar, val in zip(bars, values):
            ax.text(
                bar.get_width() + 0.02,
                bar.get_y() + bar.get_height() / 2,
                f'{val:.2f}',
                va='center',
                ha='left',
                fontsize=10,
                fontweight='bold'
            )

        ax.set_xlim(0, 1.0)
        ax.set_xlabel('归一化得分', fontsize=11)

        # 去掉多余边框
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#cccccc')
        ax.spines['left'].set_color('#cccccc')

        ax.grid(axis='x', linestyle='--', alpha=0.25)
        ax.set_title(f'{cand["name"]} 能力画像', fontsize=13, fontweight='bold', pad=15)

        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    # ---- 权重调节 ----
    st.divider()
    st.subheader("🔧 权重调节（拖动滑块，实时调整排名）")

    cols = st.columns(7)
    new_w = []
    for i, (col, ind) in enumerate(zip(cols, weights_df.columns)):
        with col:
            val = st.slider(
                ind,
                0.0, 100.0,
                float(weights_df.loc[industry, ind]),
                step=1.0,
                key=f"slider_{ind}"
            )
            new_w.append(val)

    if st.button("🔄 刷新排名", use_container_width=True):
        total = sum(new_w)
        if total > 0:
            weights_df.loc[industry] = [w / total * 100 for w in new_w]
            save_weights(weights_df)
            st.success("✅ 权重已更新，排名已刷新")
            st.rerun()

else:
    # ---- 空状态 ----
    st.info("👈 请在左侧上传简历文件")

    with st.expander("📖 使用说明", expanded=True):
        st.markdown("""
        ### 操作步骤
        1. **选择行业** → 在左侧下拉菜单中选择目标行业
        2. **上传简历** → 点击上传按钮，选择Word格式简历（支持多选）
        3. **查看排名** → 系统自动解析并计算综合得分
        4. **查看详情** → 点击候选人查看各项指标得分和能力画像
        5. **调节权重** → 拖动滑块调整权重，点击刷新查看排名变化

        ### 新增自定义行业
        1. 点击侧边栏「新增自定义行业」
        2. 输入行业名称（如「金融」）
        3. 为七个指标分配权重（总和100）
        4. 点击「添加行业」
        5. 在行业下拉菜单中选择新添加的行业
        """)