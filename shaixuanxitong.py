"""
智能简历推荐系统 —— 完整版
"""

import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False

st.set_page_config(page_title="智能简历推荐系统", page_icon="📄", layout="wide")

st.title("📄 智能简历推荐系统")
st.markdown("基于熵权法多指标评价模型 · 权重调节实时生效")


# ============ 1. 加载权重 ============
def load_weights():
    if os.path.exists("weights.xlsx"):
        try:
            df = pd.read_excel("weights.xlsx", index_col=0)
            return df
        except:
            pass
    data = {
        '教育水平': [10.35, 27.78, 5.59, 6.83, 31.23, 0.00],
        '专业对口度': [16.62, 27.28, 8.82, 3.67, 1.09, 3.15],
        '公司实力': [10.86, 11.95, 6.86, 7.04, 2.76, 0.24],
        '稳定性': [12.47, 6.78, 10.72, 12.04, 0.27, 5.41],
        '晋升速度': [9.27, 4.97, 14.63, 13.94, 12.17, 0.00],
        '重大成果': [28.77, 11.15, 29.05, 24.80, 29.17, 54.92],
        '领导力': [11.67, 10.09, 24.33, 31.69, 23.31, 36.28]
    }
    industries = ['电商', '品牌', '人力资源', '生产', '销售', '研发']
    return pd.DataFrame(data, index=industries)


# ============ 2. 加载论文数据 ============
def load_paper_data():
    norm_file = "all_industries_normalized.xlsx"
    if os.path.exists(norm_file):
        df_norm = pd.read_excel(norm_file)
        industry_map = {'production': '生产', 'hr': '人力资源', 'HR': '人力资源'}
        df_norm['industry'] = df_norm['industry'].map(industry_map).fillna(df_norm['industry'])
        return df_norm
    return None


# ============ 3. 计算排名 ============
def compute_rankings(industry, weights_df, df_norm):
    if df_norm is None:
        return None, None

    industry_data = df_norm[df_norm['industry'] == industry].copy()
    if len(industry_data) == 0:
        return None, None

    indicators = ['education_norm', 'major_match_norm', 'company_strength_norm',
                  'stability_norm', 'promotion_speed_norm', 'achievement_norm', 'leadership_norm']
    indicator_names = ['教育水平', '专业对口度', '公司实力', '稳定性', '晋升速度', '重大成果', '领导力']

    w = weights_df.loc[industry][indicator_names].values / 100

    scores = industry_data[indicators].dot(w)
    industry_data['综合得分'] = scores

    industry_data = industry_data.sort_values('综合得分', ascending=False)
    industry_data['排名'] = range(1, len(industry_data) + 1)

    df_rank = industry_data[['person_id', '综合得分', '排名']].copy()

    details = {}
    for _, row in industry_data.iterrows():
        person_id = row['person_id']
        details[person_id] = {
            name: round(row[ind], 4)
            for name, ind in zip(indicator_names, indicators)
        }

    return df_rank, details


# ============ 4. 初始化 ============
if 'weights_df' not in st.session_state:
    st.session_state.weights_df = load_weights()

if 'df_norm' not in st.session_state:
    st.session_state.df_norm = load_paper_data()

if 'industry' not in st.session_state:
    st.session_state.industry = '电商'

if 'df_rank' not in st.session_state:
    st.session_state.df_rank = None

if 'details' not in st.session_state:
    st.session_state.details = None


# ============ 5. 侧边栏 ============
with st.sidebar:
    st.header("⚙️ 参数设置")

    # ---- 行业选择 ----
    industry = st.selectbox("选择目标行业", st.session_state.weights_df.index.tolist())
    if industry != st.session_state.industry:
        st.session_state.industry = industry
        df_rank, details = compute_rankings(
            industry,
            st.session_state.weights_df,
            st.session_state.df_norm
        )
        st.session_state.df_rank = df_rank
        st.session_state.details = details

    st.divider()
    st.subheader("📤 上传简历")
    uploaded_files = st.file_uploader(
        "支持 .docx 格式（可多选）",
        type=['docx'],
        accept_multiple_files=True
    )

    if uploaded_files:
        df_rank, details = compute_rankings(
            st.session_state.industry,
            st.session_state.weights_df,
            st.session_state.df_norm
        )
        st.session_state.df_rank = df_rank
        st.session_state.details = details

    with st.expander("📊 当前行业权重"):
        w_display = st.session_state.weights_df.loc[st.session_state.industry].to_frame().T
        st.dataframe(w_display.style.format("{:.2f}%"))

    st.caption("💡 上传简历后查看排名，调节权重后点击「重新计算排名」")


# ============ 6. 主区域 ============
if uploaded_files:
    st.subheader(f"📊 {st.session_state.industry}行业候选人排名")

    if st.session_state.df_rank is None or len(st.session_state.df_rank) == 0:
        st.warning("暂无数据")
        st.stop()

    st.dataframe(
        st.session_state.df_rank.style.background_gradient(subset=['综合得分'], cmap='RdYlGn_r'),
        use_container_width=True,
        hide_index=True
    )

    st.caption(f"📌 当前使用权重：{st.session_state.industry}行业")

    st.divider()
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📋 Candidate Details")
        candidates_list = st.session_state.df_rank['person_id'].tolist()
        if len(candidates_list) > 0:
            selected_idx = st.selectbox(
                "Select Candidate",
                range(len(candidates_list)),
                format_func=lambda i: f"{i+1}. {candidates_list[i]} (Score: {st.session_state.df_rank.iloc[i]['综合得分']:.4f})"
            )

            selected_person = candidates_list[selected_idx]
            selected_score = st.session_state.df_rank.iloc[selected_idx]['综合得分']

            st.metric("综合得分", f"{selected_score:.4f}")

            if st.session_state.details and selected_person in st.session_state.details:
                detail_dict = st.session_state.details[selected_person]
                detail_df = pd.DataFrame({
                    '指标': list(detail_dict.keys()),
                    '得分': list(detail_dict.values())
                })
                st.dataframe(detail_df, hide_index=True)

    with col2:
        st.subheader("🎯 Ability Profile")
        if st.session_state.details and selected_person in st.session_state.details:
            detail_dict = st.session_state.details[selected_person]
            names = list(detail_dict.keys())
            values = list(detail_dict.values())

            name_map = {
                '教育水平': 'Education',
                '专业对口度': 'Major Match',
                '公司实力': 'Company',
                '稳定性': 'Stability',
                '晋升速度': 'Promotion',
                '重大成果': 'Achievement',
                '领导力': 'Leadership'
            }
            names_en = [name_map.get(n, n) for n in names]

            fig, ax = plt.subplots(figsize=(8, 5))
            colors = ['#2ecc71' if v >= 0.6 else '#f39c12' if v >= 0.4 else '#e74c3c' for v in values]

            bars = ax.barh(names_en, values, color=colors, height=0.6, edgecolor='white', linewidth=1)

            for bar, val in zip(bars, values):
                ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2,
                        f'{val:.2f}', va='center', ha='left', fontsize=10, fontweight='bold')

            ax.set_xlim(0, 1.0)
            ax.set_xlabel('Score', fontsize=11)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_color('#cccccc')
            ax.spines['left'].set_color('#cccccc')
            ax.grid(axis='x', linestyle='--', alpha=0.25)

            candidate_name = f'Candidate {selected_idx + 1}'
            ax.set_title(f'{candidate_name} Ability Profile', fontsize=13, fontweight='bold', pad=15)

            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

    # ---- 权重调节 ----
    st.divider()
    st.subheader("🔧 权重调节（调节后点击「重新计算排名」）")

    current_w = st.session_state.weights_df.loc[st.session_state.industry].values
    indicator_names = st.session_state.weights_df.columns.tolist()

    cols = st.columns(7)
    new_w = []
    for i, (col, ind) in enumerate(zip(cols, indicator_names)):
        with col:
            val = st.number_input(
                ind,
                min_value=0.0,
                max_value=100.0,
                value=float(current_w[i]),
                step=1.0,
                key=f"weight_{ind}"
            )
            new_w.append(val)

    total = sum(new_w)
    st.caption(f"权重总和：{total:.1f}%")

    if st.button("🔄 重新计算排名", use_container_width=True):
        if total == 0:
            st.error("权重总和不能为0！")
        else:
            norm_w = [w / total * 100 for w in new_w]
            st.session_state.weights_df.loc[st.session_state.industry] = norm_w

            df_rank, details = compute_rankings(
                st.session_state.industry,
                st.session_state.weights_df,
                st.session_state.df_norm
            )
            st.session_state.df_rank = df_rank
            st.session_state.details = details

            st.success("✅ 权重已更新，排名已重新计算！")
            st.rerun()

else:
    st.info("👈 请在左侧上传简历文件")
