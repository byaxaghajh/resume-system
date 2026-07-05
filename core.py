"""
core.py —— 论文模型核心计算模块
对应论文第三章（二）指标量化规则 + 第五章（二）综合得分公式
"""

import re


# ========== 1. 七项指标量化函数 ==========

def calc_education(edu_text):
    """
    教育水平量化（对应论文表2）
    支持：本科/硕士/博士/MBA/EMBA/大专等
    """
    edu_text = str(edu_text)

    # 优先匹配学历关键词
    if '博士' in edu_text:
        return 0.9
    if '硕士' in edu_text or '研究生' in edu_text:
        return 0.7
    if 'MBA' in edu_text or 'EMBA' in edu_text:
        return 0.7
    if '本科' in edu_text or '学士' in edu_text:
        return 0.5
    if '大专' in edu_text or '专科' in edu_text:
        return 0.3

    # 985/211/双一流院校修正
    key_univ = ['清华大学', '北京大学', '复旦大学', '上海交通大学',
                '浙江大学', '南京大学', '武汉大学', '华中科技大学',
                '华南理工大学', '中山大学', '南开大学', '天津大学']
    for uni in key_univ:
        if uni in edu_text:
            return 0.6  # 本科+名校

    return 0.3


def calc_major_match(major_text, industry):
    """
    专业对口度量化
    从专业文本中匹配行业关键词
    """
    if not major_text or str(major_text).strip() == '':
        return 0.0

    major_text = str(major_text)
    keywords = {
        '研发': ['计算机', '软件工程', '人工智能', '数据科学', '电子信息', '通信工程', '材料科学'],
        '电商': ['电子商务', '市场营销', '工商管理', '国际贸易', '物流管理'],
        '销售': ['市场营销', '工商管理', '国际贸易', '经济学', '金融学'],
        '品牌': ['广告学', '传播学', '市场营销', '新闻学', '公共关系', '品牌管理', '工商管理'],
        '人力资源': ['人力资源管理', '心理学', '劳动与社会保障', '工商管理'],
        '生产': ['工业工程', '机械工程', '自动化', '质量管理', '供应链管理']
    }

    for kw in keywords.get(industry, []):
        if kw in major_text:
            return 1.0
    return 0.0


def calc_company_power(company_text):
    """
    公司实力量化
    """
    if not company_text or str(company_text).strip() == '':
        return 0.1

    company_text = str(company_text)

    # 国际头部企业
    if any(x in company_text for x in ['Apple', 'Google', 'Microsoft', 'Amazon', 'IBM', 'Intel', 'Samsung']):
        return 1.0

    # 国内知名上市公司/集团（扩充品牌行业公司）
    if any(x in company_text for x in [
        '阿里巴巴', '腾讯', '华为', '字节跳动', '京东', '美团', '网易', '百度', '小米',
        'KLF集团', 'JY国际集团', 'MH国际控股', 'OG集团', 'LVMH', 'ALBB', 'BLY',
        '中国移动', '宁德时代', '美的集团', '格力电器', '海尔智家'
    ]):
        return 0.7

    # 中型行业领先企业
    if any(x in company_text for x in [
        '深信服', '奇安信', '旷视科技', '商汤科技', '海康威视', '大华股份', '科大讯飞',
        'LQX', 'WM生物', 'DD网络', 'KST个人护理', 'YX化妆品'
    ]):
        return 0.5

    # 启发式推断
    if '某' in company_text or 'XX' in company_text:
        return 0.1
    if '集团' in company_text:
        return 0.5
    if '股份' in company_text:
        return 0.4
    if '国际' in company_text:
        return 0.5
    if '科技' in company_text or '技术' in company_text:
        return 0.3
    if '有限公司' in company_text:
        return 0.3

    return 0.2


def calc_stability(work_years_list):
    """职业稳定性：平均在职时长（年）"""
    if not work_years_list:
        return 0.0
    return sum(work_years_list) / len(work_years_list)


def calc_promotion_speed(positions):
    """
    晋升速度（逆向指标）
    从职位列表中计算晋升速度
    """
    if not positions:
        return 8.0

    level_map = {
        '实习生': 1, '助理': 2, '专员': 3, '主管': 4,
        '经理': 5, '高级经理': 6, '总监': 7, '副总经理': 8,
        '总经理': 9, '总裁': 10, '合伙人': 9, 'CEO': 10,
        '项目负责人': 6, '负责人': 5, '店长': 4, '组长': 3
    }

    max_level = 0
    promotions = 0
    for pos in positions:
        pos = str(pos).strip()
        level = level_map.get(pos, 2)
        if level > max_level and max_level > 0:
            promotions += 1
        max_level = max(max_level, level)

    if promotions == 0:
        return 8.0
    return max(1.0, 5.0 - promotions)


def calc_achievement(project_texts):
    """
    重大成果量化
    从文本中提取业绩数据
    """
    if not project_texts:
        return 0.0

    all_text = ' '.join([str(t) for t in project_texts])

    score = 0.0

    # 检测成果关键词
    keywords = ['增长', '提升', '销售', 'GMV', '业绩', '操盘', '爆款', '翻倍',
                '突破', '达成', '完成', '创造', '实现', '同比', '环比']

    for kw in keywords:
        if kw in all_text:
            score = max(score, 0.3)

    # 匹配数字+单位（亿/万/%）
    nums = re.findall(r'(\d+\.?\d*)\s*(?:亿|万|%)', all_text)
    if nums:
        max_num = max(float(n) for n in nums)
        if max_num >= 10000:
            score = max(score, 0.9)
        elif max_num >= 1000:
            score = max(score, 0.8)
        elif max_num >= 100:
            score = max(score, 0.7)
        elif max_num >= 10:
            score = max(score, 0.5)

    # 特定模式
    if '从0到1' in all_text or '从零到一' in all_text:
        score = max(score, 0.7)
    if '年销售' in all_text and '亿' in all_text:
        score = max(score, 0.85)
    if '增长' in all_text and '%' in all_text:
        score = max(score, 0.7)
    if '操盘' in all_text:
        score = max(score, 0.6)

    return min(score, 1.0)


def calc_leadership(work_desc_list):
    """
    领导力量化
    从工作描述中提取团队管理信息
    """
    if not work_desc_list:
        return 0.0

    all_text = ' '.join([str(t) for t in work_desc_list])
    score = 0.0

    # 1. 提取下属人数
    subordinate_matches = re.findall(r'下属[：:]\s*(\d+)\s*人', all_text)
    if not subordinate_matches:
        subordinate_matches = re.findall(r'带过\s*(\d+)\s*人', all_text)
    if not subordinate_matches:
        subordinate_matches = re.findall(r'团队.*?(\d+)\s*人', all_text)

    if subordinate_matches:
        max_team = max(int(n) for n in subordinate_matches)
        if max_team >= 50:
            score += 0.7
        elif max_team >= 20:
            score += 0.6
        elif max_team >= 10:
            score += 0.5
        elif max_team >= 5:
            score += 0.4
        else:
            score += 0.3

    # 2. 管理职位关键词
    if any(x in all_text for x in ['总监', '总经理', '合伙人', '总裁', 'CEO', '副总经理']):
        score += 0.2
    elif any(x in all_text for x in ['经理', '主管', '负责人', '店长']):
        score += 0.1

    # 3. 跨部门协作
    if any(x in all_text for x in ['跨部门', '协同', '协调', '牵头']):
        score += 0.1

    return min(score, 1.0)


# ========== 2. 从简历文本中提取指标 ==========

def parse_resume(text, industry):
    """
    从简历文本中提取七项指标原始值
    支持段落和表格两种格式
    """
    result = {
        'name': '未命名',
        'education': 0.3,
        'major_match': 0.0,
        'company_strength': 0.2,
        'stability': 0.0,
        'promotion_speed': 0.0,
        'achievement': 0.0,
        'leadership': 0.0
    }

    # ===== 1. 提取姓名 =====
    name_match = re.search(r'(?:姓名|name)[：:]\s*([^\s\n]+)', text, re.IGNORECASE)
    if name_match:
        result['name'] = name_match.group(1).strip()

    # ===== 2. 提取教育水平 =====
    # 从表格中匹配教育经历
    edu_match = re.search(r'\d{4}/\d{2}-\d{4}/\d{2}.*?[丨|]\s*([^丨|]+?)[丨|]\s*(本科|硕士|博士|MBA|EMBA|大专|专科|学士)', text)
    if edu_match:
        edu_text = edu_match.group(1) + edu_match.group(2)
        result['education'] = calc_education(edu_text)
    else:
        # 从段落中匹配
        edu_match = re.search(r'(?:最高学历|学历|教育|毕业院校)[：:]\s*([^\n]+)', text)
        if edu_match:
            result['education'] = calc_education(edu_match.group(1))

    # ===== 3. 提取专业对口度 =====
    major_match = re.search(r'[丨|]\s*([^丨|]+?)[丨|]\s*(本科|硕士|博士|MBA|EMBA|大专)', text)
    if major_match:
        result['major_match'] = calc_major_match(major_match.group(1), industry)

    major_match2 = re.search(r'(?:专业|所学专业)[：:]\s*([^\n]+)', text)
    if major_match2 and result['major_match'] == 0:
        result['major_match'] = calc_major_match(major_match2.group(1), industry)

    # ===== 4. 提取公司实力 =====
    # 从工作经历表格中匹配公司名
    company_match = re.search(r'\d{4}/\d{2}-\d{4}/\d{2}.*?[丨|]\s*([^丨|]+?(?:集团|有限公司|股份|国际|科技|化妆品|网络|生物|品牌|电商|控股))', text)
    if company_match:
        result['company_strength'] = calc_company_power(company_match.group(1))
    else:
        company_match = re.search(r'(?:公司|单位|企业)[：:]\s*([^\n]+)', text)
        if company_match:
            result['company_strength'] = calc_company_power(company_match.group(1))

    # ===== 5. 提取稳定性 =====
    work_periods = re.findall(r'(\d{4}/\d{2})-(\d{4}/\d{2}|至今)', text)
    if not work_periods:
        work_periods = re.findall(r'(\d{4})\s*[-~至]\s*(\d{4}|至今)', text)

    if work_periods:
        durations = []
        for start, end in work_periods:
            try:
                start_year = int(start.split('/')[0]) if '/' in start else int(start)
                if '至今' in end:
                    end_year = 2026
                else:
                    end_year = int(end.split('/')[0]) if '/' in end else int(end)
                duration = end_year - start_year
                if duration > 0:
                    durations.append(duration)
            except:
                pass
        if durations:
            result['stability'] = sum(durations) / len(durations)

    # ===== 6. 提取晋升速度 =====
    positions = re.findall(r'[丨|]\s*([^丨|]+?)(?:总监|总经理|经理|主管|负责人|合伙人|店长|组长|专员|总裁|CEO)', text)
    if not positions:
        positions = re.findall(r'(总监|总经理|经理|主管|负责人|合伙人|店长|组长|专员|总裁|CEO)', text)
    if positions:
        result['promotion_speed'] = calc_promotion_speed(positions)

    # ===== 7. 提取重大成果 =====
    # 收集所有可能的成果描述
    project_texts = []
    for pattern in [
        r'(?:项目|成果|业绩|主要业绩|项目业绩)[：:]\s*([^\n]+)',
        r'工作职责[：:]\s*([^\n]+)',
        r'[0-9]+[、.][^\n]+'
    ]:
        matches = re.findall(pattern, text)
        project_texts.extend(matches)

    if project_texts:
        result['achievement'] = calc_achievement(project_texts)

    # ===== 8. 提取领导力 =====
    # 收集工作描述
    work_desc = re.findall(r'(?:工作职责|职责|岗位职责|工作描述)[：:]\s*([^\n]+)', text)
    # 也提取包含"下属"的句子
    subordinate_sentences = re.findall(r'[^。]*?下属[：:]\s*\d+\s*人[^。]*?。', text)
    work_desc.extend(subordinate_sentences)

    if work_desc:
        result['leadership'] = calc_leadership(work_desc)

    return result


# ========== 3. 混合归一化 + 综合评分 ==========

def calculate_scores(candidates, industry, weights_df, alpha=0.7):
    """
    计算所有候选人的综合得分
    使用混合归一化：论文极值 + 批次极值加权
    对应论文第五章公式：Score_i = Σ w_j · x_ij

    参数:
        candidates: 候选人列表
        industry: 目标行业
        weights_df: 权重DataFrame
        alpha: 论文基准权重 (0~1)，默认0.7
    """
    indicators = weights_df.columns.tolist()
    w = weights_df.loc[industry].values / 100

    PAPER_MIN = {
        'education': 0.0,
        'major_match': 0.0,
        'company_strength': 0.0,
        'stability': 0.0,
        'promotion_speed': 0.0,
        'achievement': 0.0,
        'leadership': 0.0
    }
    PAPER_MAX = {
        'education': 1.0,
        'major_match': 1.0,
        'company_strength': 1.0,
        'stability': 1.0,
        'promotion_speed': 1.0,
        'achievement': 1.0,
        'leadership': 1.0
    }

    all_raw = []
    for cand in candidates:
        raw = [
            cand['education'],
            cand['major_match'],
            cand['company_strength'],
            cand['stability'],
            cand['promotion_speed'],
            cand['achievement'],
            cand['leadership']
        ]
        raw[4] = 1.0 / (raw[4] + 0.01) if raw[4] > 0 else 0.0
        all_raw.append(raw)

    batch_min = [min(col) for col in zip(*all_raw)] if all_raw else [0] * 7
    batch_max = [max(col) for col in zip(*all_raw)] if all_raw else [1] * 7

    col_names = ['education', 'major_match', 'company_strength',
                 'stability', 'promotion_speed', 'achievement', 'leadership']

    results = []
    for cand, raw in zip(candidates, all_raw):
        norm = []
        for i, (col, val) in enumerate(zip(col_names, raw)):
            paper_min = PAPER_MIN[col]
            paper_max = PAPER_MAX[col]
            batch_min_i = batch_min[i]
            batch_max_i = batch_max[i]

            if paper_max == paper_min:
                paper_norm = 0.0
            else:
                paper_norm = max(0.0, min(1.0, (val - paper_min) / (paper_max - paper_min)))

            if batch_max_i == batch_min_i:
                batch_norm = 0.0
            else:
                batch_norm = max(0.0, min(1.0, (val - batch_min_i) / (batch_max_i - batch_min_i)))

            mixed_norm = alpha * paper_norm + (1 - alpha) * batch_norm
            norm.append(round(mixed_norm, 4))

        score = sum(w[i] * norm[i] for i in range(len(indicators)))

        results.append({
            'name': cand['name'],
            'score': round(score, 4),
            'details': dict(zip(indicators, [round(v, 4) for v in norm]))
        })

    return sorted(results, key=lambda x: x['score'], reverse=True)
