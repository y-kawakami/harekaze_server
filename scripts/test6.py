import japanize_matplotlib
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

# サンプルデータ（各行：[樹皮の状態, 樹齢]）

data = np.array([
    [3, 55],
    [5, 55],
    [2, 55],
    [3, 55],
    [4, 55],
    [2, 55],
    [3, 55],
    [4, 55],
    [5, 55],
    [3, 55],
    [4, 55],
    [5, 55],
    [3, 45],
    [4, 45],
    [5, 45],
    [3, 55],
    [3, 65],
    [4, 65],
    [5, 65],
    [3, 45],
    [4, 45],
    [3, 30],
    [4, 30],
    [2, 50],
    [1, 45],
    [2, 40],
    [2, 40],
    [2, 35],
    [3, 65],
    [4, 65],
    [2, 55],
    [3, 55],
    [2, 55],
    [3, 55],
    [5, 55],
    [3, 55],
    [5, 55],
    [3, 55],
    [5, 55],
    [3, 30],
    [4, 30],
    [4, 50],
    [2, 20],
    [1, 10],
    [4, 20],
    [5, 25],
    [4, 60],
    [4, 50],
    [3, 40],
    [3, 40],
    [4, 90],
    [4, 100],
    [4, 70],
    [5, 100],
    [4, 90],
    [4, 75],
    [5, 100],
    [5, 100],
    [4, 60],
    [4, 90],
    [3, 75],
    [3, 45],
    [3, 45],
    [3, 55],
    [3, 55],
    [3, 55],
    [5, 65],
    [3, 55],
    [3, 45],
    [3, 45],
    [3, 45],
    [3, 45],
    [2, 45],
    [2, 35],
    [2, 35],
    [2, 35],
    [3, 45],
    [2, 35],
    [2, 35],
    [2, 25],
    [1, 40],
    [2, 40],
    [4, 40],
    [2, 35],
    [2, 45],
    [2, 50],
    [1, 45],
    [5, 45],
    [2, 35],
    [2, 35],
    [3, 35],
    [1, 35],
    [2, 35],
    [2, 45],
    [2, 35],
    [3, 35],
    [2, 35],
    [2, 40],
    [3, 40],
    [3, 50]
])


# 説明変数と目的変数に分割
X = data[:, 0].reshape(-1, 1)  # 樹皮の状態
y = data[:, 1]                 # 樹齢

# 2次の多項式特徴量を作成
poly = PolynomialFeatures(degree=2)
X_poly = poly.fit_transform(X)

# 線形回帰モデルの作成と学習（多項式回帰）
model_poly = LinearRegression()
model_poly.fit(X_poly, y)

# モデルのパラメータを表示
print("切片:", model_poly.intercept_)
print("多項式回帰モデルの係数:", model_poly.coef_)

# プロットのための入力範囲の作成
x_line = np.linspace(X.min(), X.max(), 100).reshape(-1, 1)
x_line_poly = poly.transform(x_line)
y_line_poly = model_poly.predict(x_line_poly)

# 区分的に定義された関数（estimate_tree_age_v2）


def estimate_tree_age_v2(texture):
    """樹皮の状態から樹齢を推定する関数（改良版）"""
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

# 緑の点線（参考曲線）


def green_dotted_curve(t):
    if t <= 1.0:
        return 10.0
    elif t <= 2.0:
        return 25.0
    elif t <= 3.0:
        return 40.0
    elif t <= 4.0:
        return 58.0  # 4.0で58歳
    else:
        # 4.0-5.0の間は急な上昇曲線
        return 58.0 + 42.0 * ((t - 4.0) / 1.0) ** 1.5


# 新しいモデルの曲線データを生成
x_new = np.linspace(1.0, 5.0, 100).reshape(-1, 1)
y_model = np.array([estimate_tree_age_v2(t[0]) for t in x_new])
y_green = np.array([green_dotted_curve(t[0]) for t in x_new])

# 1.0-4.0の線形部分のデータ
x_linear = np.linspace(1.0, 4.0, 50).reshape(-1, 1)
y_linear = np.array([16.0 * t[0] - 6.0 for t in x_linear])

# 4.0-5.0の二次曲線部分のデータ
x_quad = np.linspace(4.0, 5.0, 50).reshape(-1, 1)
y_quad = np.array([26.0 * ((t[0] - 4.0) ** 2) +
                  16.0 * t[0] - 6.0 for t in x_quad])

# 散布図と回帰曲線のプロット
plt.figure(figsize=(10, 6))
plt.scatter(X, y, label='サンプルデータ')
plt.plot(x_line, y_line_poly, color='red', label='2次多項式回帰')

# 新しいモデルを追加（線形部分と二次曲線部分を緑の点線に統一）
plt.plot(x_linear, y_linear, color='green', linestyle='--',
         linewidth=2, label='区分的関数モデル（1.0-4.0）')
plt.plot(x_quad, y_quad, color='green', linestyle='--',
         linewidth=2, label='区分的関数モデル（4.0-5.0）')

# 参考曲線は非表示
# plt.plot(x_new, y_green, color='green', linestyle='--', linewidth=2, label='参考曲線')

plt.xlabel('樹皮の状態（樹木医診断）')
plt.ylabel('樹齢（年）')
plt.title('樹皮の状態と樹齢の関係')
plt.legend()
plt.grid(True)
plt.show()
