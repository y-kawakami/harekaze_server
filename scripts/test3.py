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
plt.title('樹皮の状態と樹齢の関係')
plt.show()

# 樹齢と幹径のデータ
# データは「幹径, 樹齢」の順に並んでいる
diameter_age_data = np.array([
    [51.0, 55],
    [56.1, 55],
    [52.9, 55],
    [53.8, 55],
    [38.9, 45],
    [39.8, 55],
    [70.4, 65],
    [49.4, 45],
    [29.9, 30],
    [47.8, 50],
    [33.8, 45],
    [39.5, 40],
    [35.0, 40],
    [42.7, 35],
    [74.8, 65],
    [61.1, 55],
    [58.9, 55],
    [60.5, 55],
    [61.5, 55],
    [47.8, 30],
    [36.6, 30],
    [56.1, 50],
    [8.0, 10],
    [20.4, 20],
    [71.7, 60],
    [38.2, 50],
    [56.7, 40],
    [46.8, 40],
    [98.7, 90],
    [73.6, 70],
    [168.8, 100],
    [98.7, 90],
    [72.9, 75],
    [136.3, 100],
    [175.2, 100],
    [125.2, 90],
    [71.0, 75],
    [47.1, 45],
    [38.5, 45],
    [59.9, 55],
    [65.6, 55],
    [66.9, 55],
    [80.6, 65],
    [51.6, 55],
    [38.5, 45],
    [51.3, 45],
    [50.0, 45],
    [44.6, 45],
    [47.8, 45],
    [33.1, 35],
    [29.9, 35],
    [33.1, 35],
    [45.5, 45],
    [25.5, 35],
    [29.6, 35],
    [23.9, 25],
    [39.2, 40],
    [31.5, 35],
    [51.3, 45],
    [58.6, 50],
    [66.9, 45],
    [41.4, 35],
    [43.3, 35],
    [36.6, 35],
    [66.9, 45],
    [58.3, 35],
    [60.8, 35],
    [74.2, 40],
    [41.7, 40],
    [67.8, 50]
])

# 説明変数と目的変数に分割（X: 樹齢, y: 幹径）
X_diameter = diameter_age_data[:, 1].reshape(-1, 1)  # 樹齢
y_diameter = diameter_age_data[:, 0]                # 幹径

# 線形回帰モデルの作成と学習
model_linear = LinearRegression()
model_linear.fit(X_diameter, y_diameter)

# 2次の多項式特徴量を作成
poly_diameter = PolynomialFeatures(degree=2)
X_diameter_poly = poly_diameter.fit_transform(X_diameter)

# 多項式回帰モデルの作成と学習
model_poly_diameter = LinearRegression()
model_poly_diameter.fit(X_diameter_poly, y_diameter)

# モデルのパラメータを表示
print("\n樹齢と幹径の関係:")
print("線形回帰の切片:", model_linear.intercept_)
print("線形回帰の係数:", model_linear.coef_)
print("多項式回帰の切片:", model_poly_diameter.intercept_)
print("多項式回帰の係数:", model_poly_diameter.coef_)

# プロットのための入力範囲の作成
x_diameter_line = np.linspace(
    X_diameter.min(), X_diameter.max(), 100).reshape(-1, 1)
y_diameter_line = model_linear.predict(x_diameter_line)
x_diameter_poly_line = poly_diameter.transform(x_diameter_line)
y_diameter_poly_line = model_poly_diameter.predict(x_diameter_poly_line)

# 散布図と回帰曲線のプロット
plt.figure(figsize=(10, 6))
plt.scatter(X_diameter, y_diameter, label='サンプルデータ')
plt.plot(x_diameter_line, y_diameter_line, color='blue', label='線形回帰')
plt.plot(x_diameter_line, y_diameter_poly_line, color='red', label='2次多項式回帰')
plt.xlabel('樹齢（年）')
plt.ylabel('幹径（cm）')
plt.legend()
plt.title('樹齢と幹径の関係')
plt.grid(True)
plt.show()

# 東京の幹径と樹齢のデータ
# データは「幹径, 樹齢」の順に並んでいる
tokyo_data = np.array([
    [51.0, 55],
    [56.1, 55],
    [52.9, 55],
    [53.8, 55],
    [38.9, 45],
    [39.8, 55],
    [70.4, 65],
    [49.4, 45],
    [29.9, 30],
    [47.8, 50],
    [33.8, 45],
    [39.5, 40],
    [35.0, 40],
    [42.7, 35],
    [74.8, 65],
    [61.1, 55],
    [58.9, 55],
    [60.5, 55],
    [61.5, 55],
    [71.0, 75],
    [47.1, 45],
    [38.5, 45],
    [59.9, 55],
    [65.6, 55],
    [66.9, 55],
    [80.6, 65],
    [51.6, 55],
    [38.5, 45],
    [51.3, 45],
    [50.0, 45],
    [44.6, 45],
    [47.8, 45],
    [33.1, 35],
    [29.9, 35],
    [33.1, 35],
    [45.5, 45],
    [25.5, 35],
    [29.6, 35],
    [23.9, 25],
    [39.2, 40],
    [31.5, 35],
    [51.3, 45],
    [58.6, 50],
    [66.9, 45],
    [41.4, 35],
    [43.3, 35],
    [36.6, 35],
    [66.9, 45],
    [58.3, 35],
    [60.8, 35],
    [74.2, 40],
    [41.7, 40],
    [67.8, 50]
])

# 説明変数と目的変数に分割（X: 樹齢, y: 幹径）
X_tokyo = tokyo_data[:, 1].reshape(-1, 1)  # 樹齢
y_tokyo = tokyo_data[:, 0]                # 幹径

# 線形回帰モデルの作成と学習
model_tokyo_linear = LinearRegression()
model_tokyo_linear.fit(X_tokyo, y_tokyo)

# 2次の多項式特徴量を作成
poly_tokyo = PolynomialFeatures(degree=2)
X_tokyo_poly = poly_tokyo.fit_transform(X_tokyo)

# 多項式回帰モデルの作成と学習
model_tokyo_poly = LinearRegression()
model_tokyo_poly.fit(X_tokyo_poly, y_tokyo)

# モデルのパラメータを表示
print("\n東京の樹齢と幹径の関係:")
print("線形回帰の切片:", model_tokyo_linear.intercept_)
print("線形回帰の係数:", model_tokyo_linear.coef_)
print("多項式回帰の切片:", model_tokyo_poly.intercept_)
print("多項式回帰の係数:", model_tokyo_poly.coef_)

# プロットのための入力範囲の作成
x_tokyo_line = np.linspace(X_tokyo.min(), X_tokyo.max(), 100).reshape(-1, 1)
y_tokyo_line = model_tokyo_linear.predict(x_tokyo_line)
x_tokyo_poly_line = poly_tokyo.transform(x_tokyo_line)
y_tokyo_poly_line = model_tokyo_poly.predict(x_tokyo_poly_line)

# 散布図と回帰曲線のプロット
plt.figure(figsize=(10, 6))
plt.scatter(X_tokyo, y_tokyo, label='東京データ', color='green')
plt.plot(x_tokyo_line, y_tokyo_line, color='blue', label='線形回帰')
plt.plot(x_tokyo_line, y_tokyo_poly_line, color='red', label='2次多項式回帰')
plt.xlabel('樹齢（年）')
plt.ylabel('幹径（cm）')
plt.legend()
plt.title('東京の樹齢と幹径の関係')
plt.grid(True)
plt.show()

# 元データと東京データの比較プロット
plt.figure(figsize=(12, 7))
plt.scatter(X_diameter, y_diameter, label='元データ', alpha=0.7)
plt.scatter(X_tokyo, y_tokyo, label='東京データ', color='green', alpha=0.7)
plt.plot(x_diameter_line, y_diameter_poly_line,
         color='blue', label='元データ 2次多項式回帰')
plt.plot(x_tokyo_line, y_tokyo_poly_line, color='red', label='東京データ 2次多項式回帰')
plt.xlabel('樹齢（年）')
plt.ylabel('幹径（cm）')
plt.legend()
plt.title('樹齢と幹径の関係比較')
plt.grid(True)
plt.show()

# 宮城の幹径と樹齢のデータ
# データは「幹径, 樹齢」の順に並んでいる
miyagi_data = np.array([
    [47.8, 30],
    [36.6, 30],
    [56.1, 50],
    [8.0, 10],
    [20.4, 20],
    [71.7, 60],
    [38.2, 50],
    [56.7, 40],
    [46.8, 40],
    [98.7, 90],
    [73.6, 70],
    [168.8, 100],
    [98.7, 90],
    [72.9, 75],
    [136.3, 100],
    [175.2, 100]
])

# 説明変数と目的変数に分割（X: 樹齢, y: 幹径）
X_miyagi = miyagi_data[:, 1].reshape(-1, 1)  # 樹齢
y_miyagi = miyagi_data[:, 0]                # 幹径

# 線形回帰モデルの作成と学習
model_miyagi_linear = LinearRegression()
model_miyagi_linear.fit(X_miyagi, y_miyagi)

# 2次の多項式特徴量を作成
poly_miyagi = PolynomialFeatures(degree=2)
X_miyagi_poly = poly_miyagi.fit_transform(X_miyagi)

# 多項式回帰モデルの作成と学習
model_miyagi_poly = LinearRegression()
model_miyagi_poly.fit(X_miyagi_poly, y_miyagi)

# モデルのパラメータを表示
print("\n宮城の樹齢と幹径の関係:")
print("線形回帰の切片:", model_miyagi_linear.intercept_)
print("線形回帰の係数:", model_miyagi_linear.coef_)
print("多項式回帰の切片:", model_miyagi_poly.intercept_)
print("多項式回帰の係数:", model_miyagi_poly.coef_)

# プロットのための入力範囲の作成
x_miyagi_line = np.linspace(X_miyagi.min(), X_miyagi.max(), 100).reshape(-1, 1)
y_miyagi_line = model_miyagi_linear.predict(x_miyagi_line)
x_miyagi_poly_line = poly_miyagi.transform(x_miyagi_line)
y_miyagi_poly_line = model_miyagi_poly.predict(x_miyagi_poly_line)

# 散布図と回帰曲線のプロット
plt.figure(figsize=(10, 6))
plt.scatter(X_miyagi, y_miyagi, label='宮城データ', color='purple')
plt.plot(x_miyagi_line, y_miyagi_line, color='blue', label='線形回帰')
plt.plot(x_miyagi_line, y_miyagi_poly_line, color='red', label='2次多項式回帰')
plt.xlabel('樹齢（年）')
plt.ylabel('幹径（cm）')
plt.legend()
plt.title('宮城の樹齢と幹径の関係')
plt.grid(True)
plt.show()

# 全データの比較プロット
plt.figure(figsize=(12, 7))
plt.scatter(X_diameter, y_diameter, label='元データ', alpha=0.6)
plt.scatter(X_tokyo, y_tokyo, label='東京データ', color='green', alpha=0.6)
plt.scatter(X_miyagi, y_miyagi, label='宮城データ', color='purple', alpha=0.6)
plt.plot(x_diameter_line, y_diameter_poly_line, color='gray',
         linestyle='--', linewidth=1, label='元データ回帰曲線')
plt.plot(x_tokyo_line, y_tokyo_poly_line, color='green',
         linestyle='--', linewidth=1, label='東京回帰曲線')
plt.plot(x_miyagi_line, y_miyagi_poly_line, color='purple',
         linestyle='--', linewidth=1, label='宮城回帰曲線')
plt.xlabel('樹齢（年）')
plt.ylabel('幹径（cm）')
plt.legend()
plt.title('全地域の樹齢と幹径の関係比較')
plt.grid(True)
plt.show()
