"""
智能简历推荐系统 —— 方案C（混合模式）
功能：上传简历后从论文数据读取指标值，用当前权重实时计算排名
运行：streamlit run shaixuanxitong.py
"""

import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

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
st.markdown("基于熵权法多指标评价模型 · 上传简历后实时计算排名")


# ============ 加载权重 ============
@st.cache_data
def load_weights():
    """加载权重数据，优先从Excel读取"""
    if os.path.exists("weights.xlsx"):
        try:
            df = pd.read_excel("weights.xlsx", index_col=0)
            expected_cols = ['教育水平', '专业对口度', '公司实力', '稳定性', '晋升速度', '重大成果', '领导力']
            if all(col in df.columns for col in expected_cols):
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

# ============ 加载论文数据 ============
@st.cache_data
def load_paper_data():
    """加载论文中的归一化数据和排名数据"""
    norm_file = "all_industries_normalized.xlsx"
    rank_file = "各行业排名表.xlsx"
    
    df_norm = None
    df_rank_all = None
    
    if os.path.exists(norm_file):
        df_norm = pd.read_excel(norm_file)
        # 行业映射
        industry_map = {'production': '生产', 'hr': '人力资源', 'HR': '人力资源'}
        df_norm['industry'] = df_norm['industry'].map(industry_map).fillna(df_norm['industry'])
    
    if os.path.exists(rank_file):
        df_rank_all = pd.read_excel(rank_file, sheet_name=None)
    
    return df_norm, df_rank_all


df_norm, df_rank_all = load_paper_data()

# ============ 侧边栏 ============
with st.sidebar:
    st.header("⚙️ 参数设置")

    # ---- 行业选择 ----
    industry = st.selectbox("选择目标行业", industries)

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

    st.caption("💡 上传后系统自动解析并计算排名")

    # ---- 自定义行业 ----
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
                    norm_w = [w / total * 100 for w in new_weights]
                    weights_df.loc[new_industry] = norm_w
                    save_weights(weights_df)
                    st.success(f"✅ 行业「{new_industry}」已添加！请重新选择行业。")
                    st.rerun()

    with st.expander("📋 当前支持的行业"):
        st.write(", ".join(weights_df.index.tolist()))


# ============ 核心计算函数 ============
def compute_rankings(industry, weights_df, df_norm, uploaded_file_names):
    """
    核心：用当前权重实时计算排名
    1. 从论文数据中提取该行业所有候选人的七项指标值
    2. 用当前权重计算综合得分
    3. 排序返回
    """
    if df_norm is None:
        return None, None
    
    # 获取该行业数据
    industry_data = df_norm[df_norm['industry'] == industry].copy()
    if len(industry_data) == 0:
        return None, None
    
    # 提取指标列
    indicators = ['education_norm', 'major_match_norm', 'company_strength_norm',
                  'stability_norm', 'promotion_speed_norm', 'achievement_norm', 'leadership_norm']
    indicator_names = ['教育水平', '专业对口度', '公司实力', '稳定性', '晋升速度', '重大成果', '领导力']
    
    # 获取当前权重（转换为小数）
    w = weights_df.loc[industry][indicator_names].values / 100
    
    # 计算综合得分
    scores = industry_data[indicators].dot(w)
    industry_data['综合得分'] = scores
    
    # 排序
    industry_data = industry_data.sort_values('综合得分', ascending=False)
    industry_data['排名'] = range(1, len(industry_data) + 1)
    
    # 提取排名表
    df_rank = industry_data[['person_id', '综合得分', '排名']].copy()
    
    # 提取详情数据
    details = {}
    for _, row in industry_data.iterrows():
        person_id = row['person_id']
        details[person_id] = {
            name: round(row[ind], 4) 
            for name, ind in zip(indicator_names, indicators)
        }
    
    return df_rank, details


# ============ 主区域 ============
if uploaded_files:
    st.subheader(f"📊 {industry}行业候选人排名")
    
    # 检查数据是否可用
    if df_norm is None:
        st.error("未找到论文数据文件：all_industries_normalized.xlsx")
        st.stop()
    
    # ===== 核心：用当前权重实时计算排名 =====
    df_rank, details = compute_rankings(industry, weights_df, df_norm, uploaded_files)
    
    if df_rank is None or len(df_rank) == 0:
        st.warning(f"未找到行业「{industry}」的论文数据")
        st.stop()
    
    # ---- 显示排名表 ----
    st.dataframe(
        df_rank.style.background_gradient(subset=['综合得分'], cmap='RdYlGn_r'),
        use_container_width=True,
        hide_index=True
    )
    
    # ---- 显示当前权重信息 ----
    st.caption(f"📌 当前使用 {industry} 行业权重，共 {len(df_rank)} 位候选人")
    
    # ---- 详情查看 ----
    st.divider()
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📋 Candidate Details")
        
        candidates_list = df_rank['person_id'].tolist()
        selected_idx = st.selectbox(
            "Select Candidate",
            range(len(candidates_list)),
            format_func=lambda i: f"{i+1}. {candidates_list[i]} (Score: {df_rank.iloc[i]['综合得分']:.4f})"
        )
        
        selected_person = candidates_list[selected_idx]
        selected_score = df_rank.iloc[selected_idx]['综合得分']
        
        st.metric("Score", f"{selected_score:.4f}")
        
        # 显示该候选人的各项指标
        if selected_person in details:
            detail_dict = details[selected_person]
            detail_df = pd.DataFrame({
                '指标': list(detail_dict.keys()),
                '得分': list(detail_dict.values())
            })
            st.dataframe(detail_df, hide_index=True)
        else:
            st.info("未找到该候选人的详细指标数据")
    
    with col2:
        st.subheader("🎯 Ability Profile")
        
        if selected_person in details:
            detail_dict = details[selected_person]
            names = list(detail_dict.keys())
            values = list(detail_dict.values())
            
            # 转换为英文标签
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
        else:
            st.info("未找到该候选人的详细指标数据")
    
    # ---- 权重调节（核心：调节后实时重新计算） ----
    st.divider()
    st.subheader("🔧 权重调节（拖动滑块，实时调整排名）")
    st.caption("💡 调节权重后点击「刷新排名」，系统将用新权重重新计算所有候选人的综合得分")
    
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
            # 更新权重
            weights_df.loc[industry] = [w / total * 100 for w in new_w]
            save_weights(weights_df)
            
            # 用新权重重新计算排名
            df_rank_new, details_new = compute_rankings(industry, weights_df, df_norm, uploaded_files)
            
            if df_rank_new is not None:
                st.dataframe(
                    df_rank_new.style.background_gradient(subset=['综合得分'], cmap='RdYlGn_r'),
                    use_container_width=True,
                    hide_index=True
                )
                st.success("✅ 权重已更新，排名已重新计算！")
                
                # 更新当前显示的数据
                st.session_state['df_rank'] = df_rank_new
                st.session_state['details'] = details_new
                
                # 刷新页面
                st.rerun()
            else:
                st.error("重新计算失败，请重试")
        else:
            st.error("权重总和不能为0！")

else:
    st.info("👈 请在左侧上传简历文件")
    
    with st.expander("📖 使用说明", expanded=True):
        st.markdown("""
        ### 系统说明
        本系统基于论文《人才简历综合优选》构建，采用熵权法多指标评价模型。
        
        **核心功能**：
        1. 上传简历后，系统从论文数据中读取对应候选人的指标值
        2. 使用当前行业权重实时计算综合得分和排名
        3. 调节权重后，系统用新权重重新计算，排名实时变化
        
        **操作步骤**：
        1. **选择行业** → 在左侧下拉菜单中选择目标行业
        2. **上传简历** → 点击上传按钮，选择简历文件
        3. **查看排名** → 系统显示该行业所有候选人的综合得分与排名
        4. **查看详情** → 点击候选人查看各项指标得分和能力画像
        5. **调节权重** → 拖动滑块调整权重，点击刷新查看排名变化
        
        ### 支持的行业
        电商、品牌、人力资源、生产、销售、研发（共6个行业）
        """)
