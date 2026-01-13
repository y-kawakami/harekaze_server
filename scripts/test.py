import japanize_matplotlib
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

# サンプルデータ（各行：[樹皮の状態, 樹齢]）
data = np.array([
    [3.97, 55],
    [3.47, 55],
    [3.35, 55],
    [4.07, 55],
    [3.63, 45],
    [3.07, 55],
    [4.36, 65],
    [3.54, 45],
    [3.75, 30],
    [3.11, 50],
    [3.93, 45],
    [3.34, 40],
    [4.74, 40],
    [3.86, 35],
    [3.77, 65],
    [3.12, 55],
    [3.94, 55],
    [3.90, 55],
    [3.99, 55],
    [3.41, 30],
    [3.90, 30],
    [3.83, 50],
    [3.41, 20],
    [2.79, 10],
    [4.11, 20],
    [3.65, 60],
    [3.98, 50],
    [3.00, 40],
    [3.17, 40],
    [4.28, 90],
    [3.89, 100],
    [3.90, 70],
    [3.78, 100],
    [3.86, 90],
    [3.97, 75],
    [4.54, 100],
    [4.65, 100],
    [3.91, 60],
    [4.24, 90],
    [3.05, 75],
    [2.90, 45],
    [2.74, 45],
    [3.79, 55],
    [3.23, 55],
    [3.11, 55],
    [3.31, 65],
    [3.34, 55],
    [3.44, 45],
    [3.06, 45],
    [3.01, 45],
    [3.45, 45],
    [3.32, 45],
    [3.43, 35],
    [3.00, 35],
    [2.67, 35],
    [2.42, 45],
    [3.79, 35],
    [3.03, 35],
    [3.87, 25],
    [3.59, 40],
    [3.42, 40],
    [3.59, 40],
    [4.98, 35],
    [3.39, 45],
    [4.99, 50],
    [4.42, 45],
    [3.62, 45],
    [3.43, 35],
    [4.05, 35],
    [3.53, 35],
    [3.32, 35],
    [3.28, 35],
    [3.76, 45],
    [4.28, 35],
    [4.27, 35],
    [4.16, 35],
    [3.78, 40],
    [3.58, 40],
    [3.01, 50]
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
