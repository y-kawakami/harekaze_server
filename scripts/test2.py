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

# 散布図と回帰曲線のプロット
plt.figure(figsize=(8, 6))
plt.scatter(X, y, label='サンプルデータ')
plt.plot(x_line, y_line_poly, color='red', label='2次多項式回帰')
plt.xlabel('樹皮の状態 (判定)')
plt.ylabel('樹齢 (正解値)')
plt.legend()
plt.show()
