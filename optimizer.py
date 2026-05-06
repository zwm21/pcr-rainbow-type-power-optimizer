#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公主连结 EX 装备战力优化模拟器 [修订版·英文文件名]
从".\data"目录读取数据，生成完整 txt 报告。
修正版：统一武器类型命名，正确匹配所有角色。
根据战力计算公式，按角色等级（current_level.txt）计算战力。
假设全部角色均已开专武、二专、6星（国服满练度环境）。
参考专栏https://www.bilibili.com/opus/1196958727754743812
"""

import re
import os
from collections import defaultdict
from datetime import datetime

# ============================================================
# 全局常量
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")          # 已改名为 data

# 读取等级
LEVEL_FILE = os.path.join(DATA_DIR, 'current_level.txt')
with open(LEVEL_FILE, 'r', encoding='utf-8') as f:
    try:
        LEVEL = int(f.read().strip())
    except:
        print(f"警告：无法从 {LEVEL_FILE} 读取等级，使用默认344级。")
        LEVEL = 344

BASE_POWER = 150
SKILL_POWER = LEVEL * 40
UE_POWER = LEVEL * 2 + 100
UE2_POWER = LEVEL * 2 + 100
SIX_STAR_POWER = LEVEL * 5 + 2000
FIXED_POWER_SUM = BASE_POWER + SKILL_POWER + UE_POWER + UE2_POWER + SIX_STAR_POWER

print(f"当前角色等级：{LEVEL}，技能战力：{SKILL_POWER}，专武：{UE_POWER}，二专：{UE2_POWER}，6星：{SIX_STAR_POWER}")
print(f"固定战力总和（假设全满）：{FIXED_POWER_SUM}")

COEFF = {
    '物攻': 1.0, '魔攻': 1.0,
    'HP': 0.1,
    '物防': 4.5, '魔防': 4.5,
    '物爆': 0.5, '魔爆': 0.5,
    'HP回复': 1.0,
    'TP回复': 0.3,
    'TP上升': 1.5,
    'TP减轻': 3.0,
    '生命偷取': 4.5,
    '治疗上升': 0.1,
    '命中': 2.0,
    '回避': 6.0,
    '物理贯通': 6.0, '魔法贯通': 6.0
}

NORMAL_TO_PRISMATIC_TYPE = {
    '弓': '彩弓',
    '拳': '彩拳套',
    '杖': '彩杖',
    '书': '彩书',
    '斧': '彩斧',
    '矛': '彩矛',
    '短剑': '彩短剑',
    '双手剑': '彩双手剑',
    '单手剑': '彩单手剑',
    '盾': '彩盾'
}

# ============================================================
# 文件解析模块
# ============================================================
def parse_base_panel(filepath):
    data = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            name = parts[0]
            stats = {}
            for part in parts[1:]:
                if ':' in part:
                    key, val = part.split(':')
                    stats[key] = float(val) if '.' in val else int(val)
            data[name] = stats
    return data

def parse_optimal_panel(filepath):
    data = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            name = parts[0]
            for part in parts[1:]:
                if part.startswith('战力:'):
                    val = int(part.split(':')[1])
                    data[name] = val
                    break
    return data

def parse_ex_equip(filepath):
    equip_pattern = re.compile(r'([^\s★]+★\d)\[(.*?)\](?:\((.*?)\))?')
    data = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(' ', 2)
            if len(parts) < 3:
                continue
            name = parts[0]
            equip_str = parts[2].replace(', ', ',')
            equips = equip_str.split(',')
            if len(equips) < 3:
                continue

            def parse_one(estr):
                m = equip_pattern.match(estr.strip())
                if not m:
                    return '', {}
                ename = m.group(1)
                inner = m.group(2)
                outer = m.group(3) if m.group(3) else ''
                bonuses = {}
                for tok in (inner + '/' + outer).split('/'):
                    tok = tok.strip()
                    if not tok:
                        continue
                    attr, val = tok.split('x')
                    attr = (attr.replace('血量','HP').replace('法爆','魔爆').replace('物爆','物爆')
                            .replace('魔攻','魔攻').replace('物攻','物攻').replace('法贯','魔法贯通')
                            .replace('物贯','物理贯通').replace('物防','物防').replace('魔防','魔防'))
                    if '%' in val:
                        val = float(val.replace('%','')) / 100.0
                    else:
                        val = float(val)
                    bonuses[attr] = bonuses.get(attr, 0) + val
                return ename, bonuses

            w_name, w_bonus = parse_one(equips[0])
            a_name, a_bonus = parse_one(equips[1])
            acc_name, acc_bonus = parse_one(equips[2])
            data[name] = {
                'weapon': w_name, 'armor': a_name, 'acc': acc_name,
                'weapon_bonus': w_bonus, 'armor_bonus': a_bonus, 'acc_bonus': acc_bonus
            }
    return data

def parse_normal_equip_types(filepath):
    mapping = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                ename = parts[0]      # 粉-天国之拳
                etype = parts[1]      # 拳
                mapping[ename] = etype
    return mapping

def parse_prismatic_info(filepath):
    info = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            fullname = parts[0]
            etype = None
            main_bonus = {}
            for i, p in enumerate(parts):
                if p == '主词条':
                    for j in range(i+1, len(parts)):
                        if parts[j] == '副词条':
                            break
                        attr_val = parts[j]
                        m = re.match(r'([\u4e00-\u9fa5]+)(\d+\.?\d*)%', attr_val)
                        if m:
                            attr = m.group(1)
                            val = float(m.group(2)) / 100.0
                            main_bonus[attr] = val
                elif p in ('彩弓','彩拳套','彩杖','彩书','彩斧','彩矛','彩短剑','彩双手剑','彩单手剑','彩盾'):
                    etype = p
            if etype:
                info[fullname] = {'type': etype, 'main_bonus': main_bonus}
    return info

# ============================================================
# 武器类型识别（统一返回彩武类型名）
# ============================================================
def get_weapon_type(weapon_name, normal_types, prismatic_info):
    base = weapon_name.split('★')[0]
    if base in prismatic_info:
        return prismatic_info[base]['type']
    if base in normal_types:
        raw_type = normal_types[base]
        return NORMAL_TO_PRISMATIC_TYPE.get(raw_type, raw_type)
    return None

# ============================================================
# 战力计算（使用新的固定战力公式）
# ============================================================
def calc_power(base_stats, total_bonus):
    new_stats = {}
    for attr, base_val in base_stats.items():
        if attr in total_bonus:
            new_val = base_val * (1 + total_bonus[attr])
        else:
            new_val = base_val
        new_stats[attr] = new_val
    power = 0
    for attr, val in new_stats.items():
        if attr in COEFF:
            power += val * COEFF[attr]
    panel_power = round(power)
    return FIXED_POWER_SUM + panel_power, panel_power

def merge_bonuses(*dicts):
    merged = defaultdict(float)
    for d in dicts:
        for k, v in d.items():
            merged[k] += v
    return dict(merged)

# ============================================================
# 任务一：满词条彩武 (20.68%攻击) 净提升排名
# ============================================================
def task_full_prismatic(base_data, equip_data, optimal_power, normal_types, prismatic_info):
    full_bonus = {
        '彩弓': {'物攻': 0.2068},
        '彩拳套': {'物攻': 0.2068},
        '彩斧': {'物攻': 0.2068},
        '彩双手剑': {'物攻': 0.2068},
        '彩单手剑': {'物攻': 0.2068},
        '彩杖': {'魔攻': 0.2068},
        '彩书': {'魔攻': 0.2068},
        '彩矛': {'物攻': 0.1936, '物爆': 0.0168},
        '彩短剑': {'物攻': 0.1868, '物爆': 0.0268},
        '彩盾': {'HP': 0.056, '物攻': 0.16}
    }
    results = []
    for name, base in base_data.items():
        if name not in equip_data or name not in optimal_power:
            continue
        cur = equip_data[name]
        w_type = get_weapon_type(cur['weapon'], normal_types, prismatic_info)
        if w_type not in full_bonus:
            continue

        # 当前总加成
        cur_total = merge_bonuses(cur['weapon_bonus'], cur['armor_bonus'], cur['acc_bonus'])
        # 用文件最优战力反推真实固定战力
        _, cur_panel = calc_power(base, cur_total)
        real_fixed = optimal_power[name] - cur_panel

        # 重算当前最优战力（反推后重新计算确保一致性）
        recalc_cur = cur_panel + real_fixed

        # 新武器总加成
        new_total = cur_total.copy()
        for attr, val in cur['weapon_bonus'].items():
            new_total[attr] -= val
        for attr, val in full_bonus[w_type].items():
            new_total[attr] = new_total.get(attr, 0) + val
        new_total = {k: v for k, v in new_total.items() if abs(v) > 1e-9}

        _, new_panel = calc_power(base, new_total)
        new_pow = new_panel + real_fixed

        file_opt = optimal_power[name]
        gain = new_pow - recalc_cur   # 净提升 = 满词条战力 - 重算当前
        results.append((gain, name, w_type, new_pow, recalc_cur, file_opt))

    results.sort(reverse=True, key=lambda x: x[0])
    return results

# ============================================================
# 任务二/三：贪心模拟
# ============================================================
class CharState:
    def __init__(self, name, base, equip_dict, normal_types, prismatic_info, actual_optimal_power):
        self.name = name
        self.base = base
        self.cur_weapon = equip_dict['weapon']
        self.cur_armor = equip_dict['armor']
        self.cur_acc = equip_dict['acc']
        self.weapon_bonus = equip_dict['weapon_bonus'].copy()
        self.armor_bonus = equip_dict['armor_bonus'].copy()
        self.acc_bonus = equip_dict['acc_bonus'].copy()
        self.total_bonus = merge_bonuses(self.weapon_bonus, self.armor_bonus, self.acc_bonus)
        
        # 计算当前面板战力贡献
        _, cur_panel = calc_power(self.base, self.total_bonus)
        # 用文件最优总战力反推真实固定战力
        self.real_fixed = actual_optimal_power - cur_panel
        
        self.cur_power = actual_optimal_power
        self.w_type = get_weapon_type(self.cur_weapon, normal_types, prismatic_info)
        self.got_new = False

    def set_weapon(self, wname, bonus):
        self.cur_weapon = wname
        self.weapon_bonus = bonus.copy()
        self.total_bonus = merge_bonuses(self.weapon_bonus, self.armor_bonus, self.acc_bonus)
        _, panel = calc_power(self.base, self.total_bonus)
        self.cur_power = self.real_fixed + panel

def simulate_greedy(base_data, equip_data, optimal_power, normal_types, prismatic_info, sub_pct, rounds):
    states = {}
    for name, base in base_data.items():
        if name in equip_data and name in optimal_power:
            # 传入 optimal_power[name] 用于初始化真实固定战力
            states[name] = CharState(name, base, equip_data[name], normal_types, prismatic_info, optimal_power[name])
    # 后面代码保持不变……

    def get_queue(w_type):
        q = []
        for name, st in states.items():
            if st.w_type == w_type and not st.got_new:
                if w_type in ('彩杖','彩书'):
                    atk = st.base.get('魔攻', 0)
                else:
                    atk = st.base.get('物攻', 0)
                q.append((atk, name))
        q.sort(reverse=True)
        return [name for _, name in q]

    def calc_boost(st, new_bonus):
        new_total = st.total_bonus.copy()
        for attr, val in st.weapon_bonus.items():
            new_total[attr] -= val
        for attr, val in new_bonus.items():
            new_total[attr] = new_total.get(attr, 0) + val
        new_total = {k:v for k,v in new_total.items() if abs(v)>1e-9}
        _, new_panel = calc_power(st.base, new_total)   # 只取面板战力
        new_pow = st.real_fixed + new_panel
        return new_pow, new_pow - st.cur_power

    def make_new_prismatic(w_type):
        if w_type in ('彩弓','彩拳套','彩斧','彩双手剑','彩单手剑'):
            return {'物攻': 0.0468 + sub_pct}
        elif w_type in ('彩杖','彩书'):
            return {'魔攻': 0.0468 + sub_pct}
        elif w_type == '彩矛':
            return {'物攻': 0.0336 + sub_pct, '物爆': 0.0168}
        elif w_type == '彩短剑':
            return {'物攻': 0.0268 + sub_pct, '物爆': 0.0268}
        elif w_type == '彩盾':
            return {'HP': 0.056, '物攻': sub_pct}
        return {}

    def simulate_type(w_type):
        queue = get_queue(w_type)
        best_chain = []
        best_gain = 0
        for i, name in enumerate(queue):
            st = states[name]
            new_bonus = make_new_prismatic(w_type)
            new_pow, boost = calc_boost(st, new_bonus)
            if boost <= 0:
                continue
            chain = [(name, None, new_bonus, boost)]
            old_weapon = st.cur_weapon
            old_bonus = st.weapon_bonus.copy()
            cur_gain = boost
            next_idx = i + 1
            while next_idx < len(queue) and old_weapon:
                found = False
                for j in range(next_idx, len(queue)):
                    cand = states[queue[j]]
                    if cand.got_new:
                        continue
                    cand_pow, cand_boost = calc_boost(cand, old_bonus)
                    if cand_boost > 0:
                        chain.append((queue[j], old_weapon, old_bonus.copy(), cand_boost))
                        cur_gain += cand_boost
                        old_weapon = cand.cur_weapon
                        old_bonus = cand.weapon_bonus.copy()
                        next_idx = j + 1
                        found = True
                        break
                if not found:
                    break
            if cur_gain > best_gain:
                best_gain = cur_gain
                best_chain = chain
        return best_chain, best_gain

    ops = []
    # 记录每轮所有类型的模拟结果用于报告
    all_type_details = []

    for rnd in range(rounds):
        all_types = ['彩弓','彩拳套','彩斧','彩单手剑','彩双手剑','彩杖','彩书','彩矛','彩短剑','彩盾']
        type_candidates = {}
        details_this_round = {}
        for wtype in all_types:
            chain, gain = simulate_type(wtype)
            type_candidates[wtype] = (chain, gain)
            # 记录摘要：总增益和链条中的第一个角色（如果有）
            first_name = chain[0][0] if chain else "无"
            details_this_round[wtype] = (gain, first_name, chain)
        best_type = max(type_candidates, key=lambda k: type_candidates[k][1])
        best_chain, best_gain = type_candidates[best_type]
        if best_gain <= 0 or not best_chain:
            print(f"第{rnd+1}轮没有正提升组合，模拟停止。")
            all_type_details.append(details_this_round)
            break
        # 执行更新
        log = {'round': rnd+1, 'type': best_type, 'steps': []}
        for idx, (cname, old, bonus, boost) in enumerate(best_chain):
            st = states[cname]
            if idx == 0:
                st.set_weapon(f"新{best_type}", bonus)
                st.got_new = True
                log['steps'].append((cname, f"新{best_type}", boost, None))
            else:
                st.set_weapon(old, bonus)
                log['steps'].append((cname, old, boost, best_chain[idx-1][0]))
        ops.append(log)
        all_type_details.append(details_this_round)
        print(f"第{rnd+1}轮完成，选择类型：{best_type}，总增益：{best_gain:.0f}")

    return ops, all_type_details

# ============================================================
# 报告生成
# ============================================================
def generate_report(full_results, ops, all_type_details, sub_pct_str, rounds, level):
    lines = []
    lines.append("============================================================")
    lines.append("       公主连结 EX 装备战力优化报告")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"角色等级：{level}（已按角色实际开专/6星/二专反推固定加成）")
    lines.append("============================================================\n")
    lines.append(f"彩装副词条：{sub_pct_str}%    分配轮次：{rounds}\n")

    # 任务一：满词条排名
    lines.append("一、满词条彩武(20.68%攻击)单角色净提升排名 (前20)\n")
    lines.append(f"{'排名':<4} {'角色':<8} {'武器类型':<10} {'满词条战力':>8} {'重算当前':>8} {'净提升':>6} {'文件原始':>8}")
    lines.append("-" * 60)
    for i, (gain, name, wtype, new_pow, recalc_cur, file_opt) in enumerate(full_results[:20], 1):
        lines.append(f"{i:<4} {name:<8} {wtype:<10} {new_pow:>8} {recalc_cur:>8} {gain:>6} {file_opt:>8}")
    lines.append("")

    # 任务二/三：贪心过程（保持不变）
    lines.append("二、贪心算法详细过程\n")
    for idx, details in enumerate(all_type_details, 1):
        lines.append(f"第{idx}轮：每种彩武类型的最佳总净增长")
        lines.append(f"{'彩武类型':<10} {'总净增长':>8}   {'主提升角色(首位)':<12}")
        lines.append("-" * 40)
        sorted_types = sorted(details.items(), key=lambda x: x[1][0], reverse=True)
        for wtype, (gain, first_name, chain) in sorted_types:
            lines.append(f"{wtype:<10} {gain:>8.0f}   {first_name:<12}")
        lines.append("")
        if idx <= len(ops):
            chosen = ops[idx-1]
            lines.append(f"本轮实际选择：{chosen['type']}，链条详情：")
            for step_idx, (cname, weapon, boost, from_who) in enumerate(chosen['steps']):
                if from_who is None:
                    lines.append(f"  -> {cname} 获得 {weapon}，战力变化 {boost:+.0f}")
                else:
                    lines.append(f"  -> {cname} 获得 {weapon}（来自 {from_who}），战力变化 {boost:+.0f}")
            lines.append(f"  本轮总净增长：{sum(s[2] for s in chosen['steps']):+.0f}")
        lines.append("")

    # 全队总净增长
    total_all = 0
    for log in ops:
        for _, _, boost, _ in log['steps']:
            total_all += boost
    lines.append(f"全队总战力净增长：{total_all:+.0f}\n")

    lines.append("============================================================")
    lines.append("报告结束")
    return "\n".join(lines)

# ============================================================
# 主程序
# ============================================================
def main():
    print("公主连结 EX 装备战力优化器")
    print(f"数据目录：{DATA_DIR}")
    print(f"角色等级：{LEVEL}")

    files = {
        'base':      os.path.join(DATA_DIR, 'base_panel_stats.txt'),
        'optimal':   os.path.join(DATA_DIR, 'optimal_panel_stats.txt'),
        'equip':     os.path.join(DATA_DIR, 'best_ex_equip_setups.txt'),
        'normal':    os.path.join(DATA_DIR, 'normal_ex_equip_info.txt'),
        'prismatic': os.path.join(DATA_DIR, 'rainbow_weapon_info.txt'),
    }

    missing = [path for path in files.values() if not os.path.exists(path)]
    if missing:
        print("错误：以下文件未找到，请检查脚本是否与 data 文件夹位于同一目录。")
        for m in missing:
            print(" ", m)
        input("按回车键退出...")
        return

    base_data = parse_base_panel(files['base'])
    optimal_power = parse_optimal_panel(files['optimal'])
    equip_data = parse_ex_equip(files['equip'])
    normal_types = parse_normal_equip_types(files['normal'])
    prismatic_info = parse_prismatic_info(files['prismatic'])

    print(f"已加载 {len(base_data)} 名角色基础面板")

    # 任务一打印
    print("\n=== 计算满词条彩武净提升 ===")
    full_results = task_full_prismatic(base_data, equip_data, optimal_power, normal_types, prismatic_info)

    print("\n满词条彩武净提升前20名：")
    print(f"{'排名':<4} {'角色':<8} {'武器类型':<10} {'满词条战力':>8} {'重算当前':>8} {'净提升':>6} {'文件原始':>8}")
    for i, (gain, name, wtype, new_pow, recalc_cur, file_opt) in enumerate(full_results[:20], 1):
        print(f"{i:<4} {name:<8} {wtype:<10} {new_pow:>8} {recalc_cur:>8} {gain:>6} {file_opt:>8}")

    # 任务二/三
    sub_pct_str = input("\n请输入彩装副词条百分比（例如8.8）：")
    try:
        sub_pct = float(sub_pct_str) / 100.0
    except:
        print("输入无效，使用默认 8.8%")
        sub_pct_str = "8.8"
        sub_pct = 0.088
    rounds_str = input("请输入模拟轮次：")
    try:
        rounds = int(rounds_str)
    except:
        print("输入无效，使用默认 5 轮")
        rounds = 5

    print(f"\n开始贪心模拟（副词条 {sub_pct_str}%，{rounds}轮）...")
    ops, all_details = simulate_greedy(base_data, equip_data, optimal_power, normal_types, prismatic_info, sub_pct, rounds)

    print("\n=== 分配结果 ===")
    total_all = 0
    for log in ops:
        print(f"\n第{log['round']}轮：{log['type']}")
        for idx, (cname, weapon, boost, from_who) in enumerate(log['steps']):
            if idx == 0:
                print(f"  {cname} 获得新彩武，提升 {boost:+.0f}")
            else:
                print(f"  {cname} 获得 {weapon}（来自 {from_who}），提升 {boost:+.0f}")
            total_all += boost
    print(f"\n全队总战力净增长：{total_all:+.0f}")

    # 生成带时间戳的报告
    report = generate_report(full_results, ops, all_details, sub_pct_str, rounds, LEVEL)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"report_{timestamp}.txt"
    report_path = os.path.join(SCRIPT_DIR, report_filename)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n报告已保存至 {report_path}")

    input("\n按回车键退出...")

if __name__ == '__main__':
    main()