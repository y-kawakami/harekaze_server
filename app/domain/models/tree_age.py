from typing import Dict

# 都道府県コードと成長係数のマッピング
# 係数は100を基準とし、小さいほど同じ樹齢でより細い幹径になる
PREFECTURE_GROWTH_FACTORS: Dict[str, float] = {
    "01": 0.6,   # 北海道
    "02": 0.8,   # 青森県
    "03": 0.8,   # 岩手県
    "04": 0.8,   # 宮城県
    "05": 0.8,   # 秋田県
    "06": 1.0,   # 山形県
    "07": 1.0,   # 福島県
    "08": 1.0,   # 茨城県
    "09": 1.0,   # 栃木県
    "10": 1.0,   # 群馬県
    "11": 1.0,   # 埼玉県
    "12": 1.0,   # 千葉県
    "13": 1.0,   # 東京都
    "14": 1.0,   # 神奈川県
    "15": 1.0,   # 新潟県
    "16": 1.0,   # 富山県
    "17": 0.8,   # 石川県
    "18": 0.8,   # 福井県
    "19": 0.8,   # 山梨県
    "20": 0.8,   # 長野県
    "21": 1.0,   # 岐阜県
    "22": 0.8,   # 静岡県
    "23": 0.8,   # 愛知県
    "24": 0.8,   # 三重県
    "25": 0.8,   # 滋賀県
    "26": 0.8,   # 京都府
    "27": 0.8,   # 大阪府
    "28": 0.8,   # 兵庫県
    "29": 0.8,   # 奈良県
    "30": 0.8,   # 和歌山県
    "31": 1.0,   # 鳥取県
    "32": 1.0,   # 島根県
    "33": 0.8,   # 岡山県
    "34": 0.8,   # 広島県
    "35": 0.8,   # 山口県
    "36": 0.8,   # 徳島県
    "37": 0.6,   # 香川県
    "38": 0.6,   # 愛媛県
    "39": 0.6,   # 高知県
    "40": 0.8,   # 福岡県
    "41": 0.8,   # 佐賀県
    "42": 0.8,   # 長崎県
    "43": 0.8,   # 熊本県
    "44": 0.8,   # 大分県
    "45": 0.6,   # 宮崎県
    "46": 0.4,   # 鹿児島県
    "47": 0.2,   # 沖縄県
}

AGE_TO_DIAMETER_MAP: Dict[float, float] = {
    0.0: 0.0,
    10.0: 15.0,
    20.0: 27.5,
    30.0: 42.5,
    40.0: 52.5,
    50.0: 61.5,
    60.0: 67.5,
    70.0: 73.5,
    80.0: 78.0,
    90.0: 82.5,
    100.0: 86.0,
    110.0: 88.0,
    120.0: 91.5
}


def estimate_tree_age(diameter) -> float:
    """
    幹径から樹齢を推定する関数

    Args:
        diameter: 幹径（センチメートル）

    Returns:
        float: 推定樹齢（年）

    Note:
        AGE_TO_DIAMETER_MAPのデータポイント間は線形補完で計算
    """
    # 入力値の検証
    if diameter <= 0:
        return 0.0

    # 最大値を超える場合は最大樹齢を返す
    max_age = max(AGE_TO_DIAMETER_MAP.keys())
    max_diameter = AGE_TO_DIAMETER_MAP[max_age]
    if diameter >= max_diameter:
        return max_age

    # 最小値より小さい場合は最小樹齢を返す
    min_age = min(AGE_TO_DIAMETER_MAP.keys())
    min_diameter = AGE_TO_DIAMETER_MAP[min_age]
    if diameter <= min_diameter:
        return min_age

    # 線形補完のために前後の値を探す
    ages = sorted(AGE_TO_DIAMETER_MAP.keys())
    for i in range(len(ages) - 1):
        age_lower = ages[i]
        age_upper = ages[i + 1]
        diameter_lower = AGE_TO_DIAMETER_MAP[age_lower]
        diameter_upper = AGE_TO_DIAMETER_MAP[age_upper]

        if diameter_lower <= diameter <= diameter_upper:
            # 線形補完で樹齢を計算
            age_ratio = (diameter - diameter_lower) / \
                (diameter_upper - diameter_lower)
            estimated_age = age_lower + age_ratio * (age_upper - age_lower)
            return estimated_age

    # 通常はここに到達しないはず
    return 0.0


'''
def estimate_tree_age(diameter):
    """
    Given the trunk diameter (cm), estimate the tree age (years).
    Inverse formula of:
        Diameter = 116 * (1 - exp(-0.015 * Age))

    Age = -(1 / 0.015) * ln(1 - diameter / 116)

    Note:
    - Valid for 0 <= diameter < 116.
      If diameter >= 116, the argument of ln() becomes 0 or negative,
      which is not defined in the real domain.
    """
    if diameter < 0:
        raise ValueError("Diameter must be non-negative.")
    if diameter >= 116:
        # Theoretically, this would lead to ln(0) or ln(negative),
        # which is invalid (t → ∞ as diameter → 116).
        diameter = 115

    return - (1.0 / 0.015) * math.log(1.0 - (diameter / 116.0))
'''


def estimate_tree_age_with_prefecture(diameter: float, prefecture_code: str) -> float:
    """
    幹径と都道府県から樹齢を計算する

    Args:
        diameter: 幹径（センチメートル）
        prefecture_code: 都道府県コード（"01": 北海道 ～ "47": 沖縄県）のように2桁の文字列

    Returns:
        TreeAge: 計算された樹齢情報

    Note:
        都道府県ごとの成長係数を適用:
        - 成長係数1.0を基準とし、小さいほど同じ樹齢でより細い幹径になる
        - 例: 北海道(0.6)では、同じ樹齢の木が標準地域の0.6倍の幹径
    """
    # 入力値の検証
    if diameter <= 0:
        return 0

    # 都道府県の成長係数の取得
    growth_factor = 1.0
    if prefecture_code in PREFECTURE_GROWTH_FACTORS:
        growth_factor = PREFECTURE_GROWTH_FACTORS[prefecture_code]

    # 都道府県の係数を考慮した実効幹径の計算
    # 成長係数が小さい地域では、同じ幹径でもより高齢になる
    effective_diameter = diameter / \
        growth_factor if growth_factor > 0 else diameter

    # 基本の樹齢計算関数を使用して計算
    tree_age = estimate_tree_age(effective_diameter)

    return tree_age


def estimate_tree_age_from_texture_old(texture_real: float) -> float:
    """
    樹皮の状態から樹齢を推定する関数

    Args:
        texture_real: 樹皮の状態を表す値（1.0-5.0）
            1.0-1.8: とても滑らか
            1.8-2.6: 滑らか
            2.6-3.4: ざらざら
            3.4-4.2: ややがさがさ
            4.2-5.0: がさがさ

    Returns:
        float: 推定樹齢（年）
    """
    # 入力値の検証
    if texture_real < 1.0:
        return 5.0  # 最小樹齢
    if texture_real > 5.0:
        return 80.0  # 最大樹齢

    # 樹皮の状態と樹齢の対応表
    texture_age_map = {
        (1.0, 1.8): (5.0, 17.5),    # とても滑らか
        (1.8, 2.6): (17.5, 32.5),   # 滑らか
        (2.6, 3.4): (32.5, 47.5),   # ざらざら
        (3.4, 4.2): (47.5, 62.5),   # ややがさがさ
        (4.2, 5.0): (62.5, 80.0),   # がさがさ
    }

    # 該当する範囲を探して線形補完
    for (texture_min, texture_max), (age_min, age_max) in texture_age_map.items():
        if texture_min <= texture_real <= texture_max:
            # 線形補完で樹齢を計算
            ratio = (texture_real - texture_min) / (texture_max - texture_min)
            return age_min + ratio * (age_max - age_min)

    # 通常はここには到達しない
    return 5.0


def estimate_tree_age_from_texture(texture: float) -> float:
    """樹皮の状態から樹齢を推定する関数（改良版）

    樹皮の状態から樹齢を推定する関数（改良版）
    グラフの緑の点線の関係に基づいて計算を行う

    樹皮の状態(diameter)が1.0-4.0の間は直線的な関係
    4.0-5.0の間はスムーズな曲線を描く

    線形関数の式を ax + b とすると、以下の条件を満たす必要があります：
    x = 1.0 のとき y = 10 (現在の条件を維持)
    x = 4.0 のとき y = 58 (新しい条件)
    これを解くと：
    a 1.0 + b = 10
    a 4.0 + b = 58
    方程式1から：b = 10 - a
    方程式2に代入：a 4.0 + (10 - a) = 58
    整理すると：4a - a + 10 = 58
    さらに整理：3a = 48
    a = 16
    b = 10 - 16 = -6
    したがって、新しい線形関数は y = 16.0 * x - 6.0 になります。
    また、4.0から5.0の範囲の二次関数も、x=4.0でy=58となるように、また接続点での傾きが連続するように調整する必要があります。
    線形部分の傾きは a = 16 なので、x = 4.0 での傾きは 16 です。
    二次関数を f(x) = c(x-4)^2 + 16x - 6 と設定すると、x=4.0で f(4.0) = 0 + 164 - 6 = 58 となり、条件を満たします。
    また、x=5.0で約100になるようにすると：
    f(5.0) = c(5-4)^2 + 165 - 6 = c + 74 ≈ 100
    c ≈ 26
    したがって、4.0-5.0の範囲の二次関数は y = 26.0 * ((x - 4.0) ** 2) + 16.0 * x - 6.0 となります。
    緑の点線の関数も、x=4.0でy=58となるように調整します。

    Args:
        texture: 樹皮の状態を表す値（1.0-5.0）

    Returns:
        float: 推定樹齢（年）
    """
    if texture <= 0:
        return 0.0

    # 入力値の範囲を制限
    if texture < 1.0:
        texture = 1.0
    if texture > 5.0:
        texture = 5.0

    # 区分的に定義された関数
    if 1.0 <= texture <= 4.0:
        # 1.0-4.0の間は線形関数
        # (1.0, 10), (4.0, 58)
        return 16.0 * texture - 6.0
    else:
        # 4.0-5.0の間は二次関数
        # x=4.0でy=58、x=5.0でy≈100
        return 26.0 * ((texture - 4.0) ** 2) + 16.0 * texture - 6.0
