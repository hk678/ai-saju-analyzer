"""
사주 시각화 모듈
- 오행 분포 차트
- 십성 분포도
- 대운 흐름 그래프

[대운 데이터 구조 대응]
daewun_list 각 항목은 _build_pillar_block 구조:
  d["간지"]["천간"] + d["간지"]["지지"]  → 간지 문자열
  d["지지"]["오행"]                      → 오행
  d["시작나이"]                          → 시작 나이
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import numpy as np
import os

# ── 한글 폰트 설정 ────────────────────────────────────────────────────────────
def setup_font():
    font_candidates = [
        "C:/Windows/Fonts/malgun.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in font_candidates:
        if os.path.exists(path):
            fm.fontManager.addfont(path)
            prop = fm.FontProperties(fname=path)
            plt.rcParams['font.family'] = prop.get_name()
            return prop.get_name()
    for font in fm.findSystemFonts():
        if any(k in font.lower() for k in ['nanum', 'gothic', 'cjk', 'korean']):
            fm.fontManager.addfont(font)
            prop = fm.FontProperties(fname=font)
            plt.rcParams['font.family'] = prop.get_name()
            return prop.get_name()
    plt.rcParams['font.family'] = 'DejaVu Sans'
    return 'DejaVu Sans'

FONT_NAME = setup_font()
plt.rcParams['axes.unicode_minus'] = False

ELEMENT_COLORS = {
    "목": "#4CAF50",
    "화": "#F44336",
    "토": "#FF9800",
    "금": "#9E9E9E",
    "수": "#2196F3",
}


def draw_element_chart(saju_data: dict, output_path: str) -> str:
    """오행 분포 막대 + 레이더 차트"""
    elements = saju_data["오행분포"]
    names  = list(elements.keys())
    values = list(elements.values())
    colors = [ELEMENT_COLORS[n] for n in names]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor('#1a1a2e')

    # 막대 차트
    ax1 = axes[0]
    ax1.set_facecolor('#16213e')
    bars = ax1.bar(names, values, color=colors, width=0.6, edgecolor='white', linewidth=0.5)
    for bar, val in zip(bars, values):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                 str(val), ha='center', va='bottom', color='white',
                 fontsize=14, fontweight='bold', fontproperties=FONT_NAME)
    ax1.set_title('오행 분포', color='white', fontsize=16, fontweight='bold',
                  fontproperties=FONT_NAME, pad=15)
    ax1.set_ylim(0, max(values) + 1)
    ax1.tick_params(colors='white', labelsize=13)
    ax1.spines[:].set_color('#444')
    for label in ax1.get_xticklabels():
        label.set_fontproperties(FONT_NAME)
        label.set_color('white')
        label.set_fontsize(14)
    ax1.set_yticks([])

    # 레이더 차트
    fig.delaxes(axes[1])
    ax2 = fig.add_subplot(122, projection='polar')
    ax2.set_facecolor('#16213e')
    N = 5
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    vals = values + values[:1]
    ax2.set_theta_offset(np.pi / 2)
    ax2.set_theta_direction(-1)
    ax2.set_rlabel_position(0)
    for i in range(1, 5):
        ax2.plot(angles, [i]*6, color='#444', linewidth=0.5, linestyle='--', alpha=0.5)
    ax2.plot(angles, vals, 'o-', linewidth=2, color='#e94560')
    ax2.fill(angles, vals, alpha=0.25, color='#e94560')
    ax2.set_xticks(angles[:-1])
    ax2.set_xticklabels(names, color='white', size=13, fontproperties=FONT_NAME)
    ax2.set_yticks([1,2,3,4])
    ax2.set_yticklabels(['1','2','3','4'], color='#888', size=8)
    ax2.tick_params(colors='white')
    ax2.spines['polar'].set_color('#444')
    ax2.set_facecolor('#16213e')
    ax2.set_title('오행 균형도', color='white', fontsize=16, fontweight='bold',
                  fontproperties=FONT_NAME, pad=20)

    name = saju_data['기본정보']['이름']
    ilju = saju_data['사주원국']['일주']['간지']
    fig.suptitle(f"{name}님 사주 오행 분석 ({ilju}일주)",
                 color='white', fontsize=17, fontweight='bold',
                 fontproperties=FONT_NAME, y=1.02)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='#1a1a2e', edgecolor='none')
    plt.close()
    return output_path


def draw_sipsung_chart(saju_data: dict, output_path: str) -> str:
    """십성 분포 파이 차트"""
    sipsung   = saju_data["십성"]
    labels    = list(sipsung.values()) + ["비견(일간)"]
    positions = list(sipsung.keys())   + ["일간"]

    SIPSUNG_COLORS = {
        "비견": "#4CAF50", "겁재": "#8BC34A",
        "식신": "#FF9800", "상관": "#FF5722",
        "편재": "#F44336", "정재": "#E91E63",
        "편관": "#9C27B0", "정관": "#673AB7",
        "편인": "#2196F3", "정인": "#03A9F4",
        "비견(일간)": "#4CAF50",
    }
    colors = [SIPSUNG_COLORS.get(l, '#999') for l in labels]

    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#1a1a2e')

    wedges, texts, _ = ax.pie(
        [1]*len(labels),
        labels=[f"{p}\n{l}" for p, l in zip(positions, labels)],
        colors=colors,
        autopct='',
        startangle=90,
        wedgeprops=dict(edgecolor='#1a1a2e', linewidth=2),
    )
    for t in texts:
        t.set_color('white')
        t.set_fontsize(12)
        t.set_fontproperties(FONT_NAME)

    ax.set_title('십성 구성도', color='white', fontsize=16, fontweight='bold',
                 fontproperties=FONT_NAME)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='#1a1a2e', edgecolor='none')
    plt.close()
    return output_path


def draw_daewun_flow(saju_data: dict, output_path: str) -> str:
    """
    대운 흐름 그래프.
    대운 항목 구조: _build_pillar_block + "시작나이"
      d["간지"]["천간"] + d["간지"]["지지"]  → 간지 문자
      d["지지"]["오행"]                      → 오행
      d["시작나이"]                          → 나이
    """
    daewun_list = saju_data["대운"]

    day_elem = saju_data["일간정보"]["오행"]
    GENERATE     = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}
    GENERATED_BY = {v: k for k, v in GENERATE.items()}
    OVERCOME     = {"목": "토", "화": "금", "토": "수", "금": "목", "수": "화"}

    def calc_luck_score(elem):
        if elem == day_elem:                   return 7
        if GENERATED_BY.get(day_elem) == elem: return 8
        if GENERATE.get(day_elem) == elem:     return 6
        if OVERCOME.get(day_elem) == elem:     return 4
        return 5

    # ── 새 구조에서 값 추출 ──────────────────────────────────────────────────
    ages   = [d["시작나이"] for d in daewun_list]
    labels = [d["간지"]["천간"] + d["간지"]["지지"] for d in daewun_list]
    elems  = [d["지지"]["오행"] for d in daewun_list]
    scores = [calc_luck_score(e) for e in elems]
    colors = [ELEMENT_COLORS.get(e, "#999") for e in elems]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    fig.patch.set_facecolor('#1a1a2e')

    # 라인 차트
    ax1.set_facecolor('#16213e')
    ax1.plot(ages, scores, 'o-', color='#e94560', linewidth=2.5, markersize=8, zorder=3)
    ax1.fill_between(ages, scores, alpha=0.2, color='#e94560')
    for age, score, label in zip(ages, scores, labels):
        ax1.annotate(label, (age, score), textcoords="offset points",
                     xytext=(0, 10), ha='center', color='white', fontsize=12,
                     fontproperties=FONT_NAME)
    ax1.set_title('대운 흐름도', color='white', fontsize=16, fontweight='bold',
                  fontproperties=FONT_NAME)
    ax1.set_xlabel('나이', color='white', fontproperties=FONT_NAME)
    ax1.set_ylabel('운세 강도', color='white', fontproperties=FONT_NAME)
    ax1.tick_params(colors='white')
    ax1.spines[:].set_color('#444')
    ax1.set_ylim(0, 10)
    ax1.grid(axis='y', color='#333', alpha=0.5)

    # 컬러 바
    ax2.set_facecolor('#16213e')
    for age, label, elem, color in zip(ages, labels, elems, colors):
        ax2.barh(0, 9, left=age, height=0.6, color=color, alpha=0.8,
                 edgecolor='white', linewidth=0.5)
        ax2.text(age + 4.5, 0, f"{label}\n({elem})",
                 ha='center', va='center', color='white', fontsize=11,
                 fontproperties=FONT_NAME, fontweight='bold')
    ax2.set_xlim(ages[0] - 1, ages[-1] + 10)
    ax2.set_ylim(-0.5, 0.5)
    ax2.set_yticks([])
    ax2.set_xlabel('나이', color='white', fontproperties=FONT_NAME)
    ax2.set_title('대운 오행 흐름', color='white', fontsize=14, fontweight='bold',
                  fontproperties=FONT_NAME)
    ax2.tick_params(colors='white')
    ax2.spines[:].set_color('#444')

    legend_patches = [mpatches.Patch(color=ELEMENT_COLORS[e], label=e)
                      for e in ["목","화","토","금","수"]]
    ax2.legend(handles=legend_patches, loc='upper right',
               facecolor='#16213e', edgecolor='#444',
               labelcolor='white', prop={'family': FONT_NAME})

    name = saju_data['기본정보']['이름']
    fig.suptitle(f"{name}님 대운 흐름 분석", color='white',
                 fontsize=17, fontweight='bold', fontproperties=FONT_NAME)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='#1a1a2e', edgecolor='none')
    plt.close()
    return output_path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from saju_calculator import calculate_saju, get_seun, get_wolun
    from datetime import datetime

    data = calculate_saju("홍길동", 1990, 5, 15, 10, "남")
    d_stem   = data["일간정보"]["일간"]
    y_branch = data["사주원국"]["연주"]["지지"]
    today    = datetime.now().year
    data["세운"] = [get_seun(today + i, d_stem, y_branch) for i in range(10)]
    data["월운"] = [get_wolun(today, m, d_stem, y_branch) for m in range(1, 13)]

    os.makedirs("/tmp/saju_test", exist_ok=True)
    draw_element_chart(data, "/tmp/saju_test/elements.png")
    draw_sipsung_chart(data, "/tmp/saju_test/sipsung.png")
    draw_daewun_flow(data,   "/tmp/saju_test/daewun.png")
    print("차트 생성 완료: /tmp/saju_test/")