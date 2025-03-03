import matplotlib.pyplot as plt
import numpy as np


def plot_tree_age_formula():
    """
    樹齢計算式をプロットする関数
    """
    # プロット用の幹径範囲を設定（0cmから120cmまで）
    diameters = np.linspace(0, 120, 500)

    # 樹齢計算用の係数
    a = 0.014  # 2次の係数
    b = -0.12  # 1次の係数
    c = 8.0    # 定数項

    # 樹齢を計算
    ages = a * (diameters ** 2) + b * diameters + c

    # TreeAge.calculate_from_diameterを使った結果
    tree_ages = [TreeAge.calculate_from_diameter(d).age for d in diameters]

    # プロット作成
    plt.figure(figsize=(10, 6))

    # 計算式のカーブをプロット
    plt.plot(diameters, ages, 'r-', label='樹齢計算式: 0.014x² - 0.12x + 8.0')

    # 実際のTreeAge計算結果をプロット
    plt.plot(diameters, tree_ages, 'b--',
             label='TreeAge.calculate_from_diameter結果')

    # 特定のデータポイントを強調表示
    key_diameters = [20, 40, 60, 80, 100]
    key_ages = [a * (d ** 2) + b * d + c for d in key_diameters]

    plt.scatter(key_diameters, key_ages, color='green',
                s=100, zorder=5, label='主要データポイント')

    # データポイントにラベルを追加
    for d, age in zip(key_diameters, key_ages):
        plt.annotate(
            f"({d}cm, {round(age)}歳)",
            xy=(d, age),
            xytext=(0, 10),
            textcoords='offset points',
            ha='center',
            fontsize=10
        )

    # 各都道府県の成長係数による曲線
    for prefecture, factor in [("01", 0.6), ("13", 1.0), ("47", 0.2)]:
        pref_name = {
            "01": "北海道 (0.6)",
            "13": "東京 (1.0)",
            "47": "沖縄 (0.2)"
        }[prefecture]

        # 実効幹径を計算
        effective_diameters = diameters / \
            float(TreeAge.PREFECTURE_GROWTH_FACTORS[prefecture])
        # 樹齢を計算
        pref_ages = [a * (d ** 2) + b * d + c for d in effective_diameters]

        plt.plot(diameters, pref_ages, '--', label=f'{pref_name}')

    plt.title('幹径と樹齢の関係')
    plt.xlabel('幹径 (cm)')
    plt.ylabel('樹齢 (年)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()

    # 0から始まるようにする
    plt.xlim(0, 120)
    plt.ylim(0, max(ages) * 1.1)

    # グラフを表示
    plt.tight_layout()
    plt.savefig('tree_age_plot.png', dpi=300)
    plt.show()


if __name__ == "__main__":
    plot_tree_age_formula()
