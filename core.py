"""
core.py —— 论文模型核心计算模块
对应论文第三章（二）指标量化规则 + 第五章（二）综合得分公式
"""

import re


# ========== 1. 七项指标量化函数 ==========

def calc_education(edu_text):
    """教育水平量化（对应论文表2）"""
    if '博士' in edu_text:
        score = 0.9
    elif '硕士' in edu_text or '研究生' in edu_text:
        score = 0.7
    elif '本科' in edu_text or '学士' in edu_text:
        score = 0.5
    else:
        score = 0.3

    key_univ = ['清华大学', '北京大学', '复旦大学', '上海交通大学',
                '浙江大学', '南京大学', '武汉大学', '华中科技大学']
    for uni in key_univ:
        if uni in edu_text:
            score = min(score + 0.1, 1.0)
            break
    return score


def calc_major_match(major_text, industry):
    """专业对口度量化"""
    keywords = {
        '研发': ['计算机', '软件工程', '人工智能', '数据科学', '电子信息'],
        '电商': ['电子商务', '市场营销', '工商管理', '国际贸易', '物流管理'],
        '销售': ['市场营销', '工商管理', '国际贸易', '经济学', '金融学'],
        '品牌': ['广告学', '传播学', '市场营销', '新闻学', '公共关系'],
        '人力资源': ['人力资源管理', '心理学', '劳动与社会保障', '工商管理'],
        '生产': ['工业工程', '机械工程', '自动化', '质量管理', '供应链管理']
    }
    for kw in keywords.get(industry, []):
        if kw in major_text or major_text in kw:
            return 1.0
    return 0.0


def calc_company_power(company_text):
    """公司实力量化"""
    company_map = {
        '华为': 0.7, '阿里巴巴': 0.7, '腾讯': 0.7, '字节跳动': 0.7,
        '百度': 0.7, '小米': 0.7, '京东': 0.7, '美团': 0.7,
        'Apple': 1.0, 'Google': 1.0, 'Microsoft': 1.0, 'Amazon': 1.0
    }
    for name, score in company_map.items():
        if name in company_text:
            return score

    if '某' in company_text or 'XX' in company_text:
        return 0.1
    elif '集团' in company_text:
        return 0.5
    elif '股份' in company_text:
        return 0.4
    elif '国际' in company_text:
        return 0.6
    elif '科技' in company_text or '技术' in company_text:
        return 0.3
    return 0.2


def calc_stability(work_years_list):
    """职业稳定性：平均在职时长（年）"""
    if not work_years_list:
        return 0.0
    return sum(work_years_list) / len(work_years_list)


def calc_promotion_speed(positions):
    """晋升速度（逆向指标）"""
    level_map = {
        '实习生': 1, '助理': 2, '专员': 3, '主管': 4,
        '经理': 5, '高级经理': 6, '总监': 7, '总经理': 8
    }
    max_level = 0
    promotions = 0
    for pos in positions:
        level = level_map.get(pos, 2)
        if level > max_level and max_level > 0:
            promotions += 1
        max_level = max(max_level, level)

    if promotions == 0:
        return 8.0
    return max(1.0, 5.0 - promotions)


def calc_achievement(project_texts, industry):
    """重大成果量化"""
    keywords = {
        '研发': ['专利', '论文', '项目经费', '技术突破', '创新'],
        '电商': ['GMV', '交易额', '转化率', '销售额', '流量'],
        '销售': ['销售额', '业绩', '增长率', '客户', '签约'],
        '品牌': ['曝光量', '转化率', '品牌影响力', '营销'],
        '人力资源': ['招聘', '培训', '员工满意度', '人才'],
        '生产': ['产能', '良率', '成本降低', '效率', '质量']
    }

    scores = []
    for text in project_texts:
        score = 0.0
        for kw in keywords.get(industry, []):
            if kw in text:
                score = max(score, 0.7)
                break

        nums = re.findall(r'(\d+\.?\d*)', text)
        if nums and score > 0:
            max_num = max(float(n) for n in nums)
            if max_num >= 10000:
                score = min(score + 0.25, 1.0)
            elif max_num >= 1000:
                score = min(score + 0.15, 1.0)
            elif max_num >= 100:
                score = min(score + 0.1, 1.0)

        if '显著增长' in text or '大幅提升' in text:
            score = max(score, 0.5)

        scores.append(score)
    return max(scores) if scores else 0.0


def calc_leadership(work_desc_list, project_list):
    """领导力量化"""
    score = 0.0

    for desc in work_desc_list:
        matches = re.findall(r'管理\s*(\d+)\s*人', desc)
        if matches:
            size = int(matches[0])
            if size >= 20:
                score += 0.7
            elif size >= 10:
                score += 0.6
            elif size >= 5:
                score += 0.5
            else:
                score += 0.3
            break

    for desc in work_desc_list:
        if '总监' in desc:
            score += 0.2
            break
        elif '总经理' in desc:
            score += 0.25
            break
        elif '经理' in desc:
            score += 0.1
            break

    for proj in project_list:
        if '跨部门' in proj:
            score += 0.2
            break
        elif '协同' in proj or '牵头' in proj:
            score += 0.1
            break

    return min(score, 1.0)


# ========== 2. 从简历文本中提取指标 ==========

def parse_resume(text, industry):
    """
    从简历文本中提取七项指标原始值
    """
    result = {
        'name': '未命名',
        'education': 0.5,
        'major_match': 0.0,
        'company_strength': 0.2,
        'stability': 0.0,
        'promotion_speed': 0.0,
        'achievement': 0.0,
        'leadership': 0.0
    }

    name_match = re.search(r'(?:姓名|name)[：:]\s*([^\s\n]+)', text, re.IGNORECASE)
    if name_match:
        result['name'] = name_match.group(1)

    edu_match = re.search(r'(?:最高学历|学历|教育)[：:]\s*([^\n]+)', text)
    if edu_match:
        result['education'] = calc_education(edu_match.group(1))

    major_match = re.search(r'(?:专业|所学专业)[：:]\s*([^\n]+)', text)
    if major_match:
        result['major_match'] = calc_major_match(major_match.group(1), industry)

    company_match = re.search(r'(?:公司|单位|企业)[：:]\s*([^\n]+)', text)
    if company_match:
        result['company_strength'] = calc_company_power(company_match.group(1))

    years = re.findall(r'(\d{4})\s*[-~至]\s*(\d{4})', text)
    if years:
        durations = [int(end) - int(start) for start, end in years]
        result['stability'] = calc_stability(durations)

    positions = re.findall(r'(?:职位|岗位)[：:]\s*([^\n]+)', text)
    if not positions:
        positions = re.findall(r'[专员助理主管经理总监总经理]+', text)
    if positions:
        result['promotion_speed'] = calc_promotion_speed(positions)

    projects = re.findall(r'(?:项目|成果|业绩)[：:]\s*([^\n]+)', text)
    if projects:
        result['achievement'] = calc_achievement(projects, industry)

    work_desc = re.findall(r'(?:工作描述|职责|岗位职责)[：:]\s*([^\n]+)', text)
    if work_desc:
        result['leadership'] = calc_leadership(work_desc, projects)

    return result


# ========== 3. 混合归一化 + 综合评分 ==========

def calculate_scores(candidates, industry, weights_df, alpha=0.7):
    """
    计算所有候选人的综合得分
    使用混合归一化：论文极值 + 批次极值加权
    对应论文第五章公式：Score_i = Σ w_j · x_ij
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