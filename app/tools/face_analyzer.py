import argparse
import glob
import io
import os
import sys
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from PIL import Image

from app.domain.models.bounding_box import BoundingBox


class FaceAnalyzer:
    """
    AWS Rekognitionの顔検出・分析機能を使用して、
    画像内の顔の感情情報とバウンディングボックスを検出するクラス
    """

    def __init__(self, min_confidence: float = 50.0):
        """
        初期化メソッド

        Args:
            min_confidence (float): 顔検出の最小信頼度閾値（0〜100）
        """
        self.min_confidence = min_confidence

        # Rekognitionクライアントの初期化はここで行わず、必要時に初期化
        self._rekognition_client = None

    def _get_rekognition_client(self):
        """
        AWS Rekognitionクライアントを取得する（必要に応じて初期化）

        Returns:
            boto3.client: Rekognitionクライアント
        """
        if self._rekognition_client is None:
            self._rekognition_client = boto3.client(
                'rekognition', region_name='ap-northeast-1')
        return self._rekognition_client

    def detect_faces(self, pil_image: Image.Image) -> List[Dict[str, Any]]:
        """
        PIL画像を入力として、AWS Rekognitionを使用して顔検出と感情分析を行う

        Args:
            pil_image (PIL.Image.Image): 検出対象の画像

        Returns:
            List[Dict[str, Any]]: 検出された顔の情報リスト。各要素には以下の情報が含まれる：
                - bounding_box (BoundingBox): 顔の位置情報
                - emotions (List[Dict[str, Any]]): 感情情報のリスト
                - confidence (float): 顔検出の信頼度
                - age_range (Dict[str, int]): 推定年齢範囲
                - gender (Dict[str, Any]): 推定性別情報
        """
        # PIL画像をバイトストリームに変換
        img_byte_arr = io.BytesIO()
        pil_image.save(
            img_byte_arr, format=pil_image.format if pil_image.format else 'JPEG')
        img_bytes = img_byte_arr.getvalue()

        try:
            # Rekognitionクライアントを取得
            rekognition = self._get_rekognition_client()

            # DetectFaces APIを呼び出して顔分析
            response = rekognition.detect_faces(
                Image={'Bytes': img_bytes},
                Attributes=['ALL']  # すべての属性を取得（感情、年齢、性別など）
            )

            # 検出された顔情報を抽出して整形
            return self.extract_face_details(response)

        except ClientError as e:
            # エラーハンドリング
            print(f"AWS Rekognition APIエラー: {e}")
            return []
        except Exception as e:
            # その他のエラー
            print(f"予期しないエラー: {e}")
            return []

    def extract_face_details(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        AWS Rekognitionのレスポンスから顔の詳細情報を抽出する

        Args:
            response (Dict[str, Any]): AWS Rekognitionのレスポンス

        Returns:
            List[Dict[str, Any]]: 検出された顔の詳細情報リスト
        """
        results = []

        # レスポンス内の顔情報を処理
        for face_detail in response.get("FaceDetails", []):
            confidence = face_detail.get("Confidence", 0)

            # 信頼度が閾値以上の場合のみ処理
            if confidence >= self.min_confidence:
                # バウンディングボックス情報の抽出
                bbox_dict = face_detail.get("BoundingBox", {})
                bbox = BoundingBox.from_dict(bbox_dict, confidence)

                # 感情情報の抽出（信頼度順にソート）
                emotions = face_detail.get("Emotions", [])
                emotions.sort(key=lambda x: x.get(
                    "Confidence", 0), reverse=True)

                # 顔の詳細情報を辞書として構築
                face_info = {
                    "bounding_box": bbox,
                    "emotions": emotions,
                    "confidence": confidence,
                    "age_range": face_detail.get("AgeRange", {}),
                    "gender": face_detail.get("Gender", {}),
                    "smile": face_detail.get("Smile", {}),
                    "eyeglasses": face_detail.get("Eyeglasses", {}),
                    "sunglasses": face_detail.get("Sunglasses", {}),
                    "beard": face_detail.get("Beard", {}),
                    "mustache": face_detail.get("Mustache", {}),
                    "eyes_open": face_detail.get("EyesOpen", {}),
                    "mouth_open": face_detail.get("MouthOpen", {})
                }

                results.append(face_info)

        return results

    def get_dominant_emotions(self, face_details: List[Dict[str, Any]], top_n: int = 1) -> List[Dict[str, Any]]:
        """
        各顔の主要な感情を取得する

        Args:
            face_details (List[Dict[str, Any]]): 顔詳細情報のリスト
            top_n (int): 取得する感情の数（上位N個）

        Returns:
            List[Dict[str, Any]]: 各顔の主要感情情報。各要素は以下の形式：
                {
                    "face_index": 顔のインデックス,
                    "bounding_box": バウンディングボックス,
                    "top_emotions": [{"Type": 感情タイプ, "Confidence": 信頼度}, ...]
                }
        """
        results = []

        for i, face in enumerate(face_details):
            emotions = face.get("emotions", [])
            top_emotions = emotions[:min(top_n, len(emotions))]

            results.append({
                "face_index": i,
                "bounding_box": face.get("bounding_box"),
                "top_emotions": top_emotions
            })

        return results

    def format_bounding_boxes(self,
                              face_details: List[Dict[str, Any]],
                              image_width: Optional[int] = None,
                              image_height: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        顔のバウンディングボックスを指定されたフォーマットに変換する

        Args:
            face_details (List[Dict[str, Any]]): 顔詳細情報のリスト
            image_width (Optional[int]): 元画像の幅
            image_height (Optional[int]): 元画像の高さ

        Returns:
            List[Dict[str, Any]]: 変換された顔情報のリスト。各要素は以下の形式：
                {
                    "bbox": (x1, y1, x2, y2, confidence),
                    "emotions": [{"Type": 感情タイプ, "Confidence": 信頼度}, ...],
                    "age_range": {"Low": 最小年齢, "High": 最大年齢},
                    "gender": {"Value": 性別, "Confidence": 信頼度}
                }
        """
        formatted_results = []

        for face in face_details:
            bbox = face.get("bounding_box")
            if bbox:
                corners = bbox.to_corners(image_width, image_height)

                formatted_face = {
                    "bbox": (*corners, bbox.confidence),
                    "emotions": face.get("emotions", []),
                    "age_range": face.get("age_range", {}),
                    "gender": face.get("gender", {})
                }

                formatted_results.append(formatted_face)

        return formatted_results


def get_face_analyzer() -> FaceAnalyzer:
    """FaceAnalyzerのインスタンスを取得する"""
    return FaceAnalyzer()


def main():
    """
    メイン実行関数。コマンドラインから画像ディレクトリを受け取り、
    感情分析を実行してHTMLレポートを生成する。
    """
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='顔感情分析ツール')
    parser.add_argument('image_dir', help='画像ファイルが格納されているディレクトリパス')
    parser.add_argument('--output', '-o', default='emotion_analysis.html',
                        help='出力するHTMLファイルのパス（デフォルト: emotion_analysis.html）')
    args = parser.parse_args()

    # 画像ディレクトリの存在確認
    if not os.path.isdir(args.image_dir):
        print(f"エラー: 指定されたディレクトリが見つかりません: {args.image_dir}")
        sys.exit(1)

    # 画像ファイルの検索
    image_files = []

    # 各拡張子でファイルを検索
    for ext in ['jpg', 'jpeg', 'png']:
        pattern = os.path.join(args.image_dir, f'*.{ext}')
        image_files.extend(glob.glob(pattern))
        # 大文字拡張子のファイルも検索
        pattern = os.path.join(args.image_dir, f'*.{ext.upper()}')
        image_files.extend(glob.glob(pattern))

    if not image_files:
        print(f"エラー: 指定されたディレクトリに画像ファイルが見つかりません: {args.image_dir}")
        sys.exit(1)

    # ファイル名でソート
    image_files.sort(key=lambda x: os.path.basename(x))

    print(f"{len(image_files)}個の画像ファイルが見つかりました。分析を開始します...")

    # 顔分析器の初期化
    face_analyzer = get_face_analyzer()

    # 分析結果を格納するリスト
    all_results = []

    # 各画像を処理
    for image_path in image_files:
        try:
            # 画像の読み込み
            pil_image = Image.open(image_path)

            # 顔検出
            faces = face_analyzer.detect_faces(pil_image)

            # 結果を格納
            all_results.append({
                "image_path": image_path,
                "faces": faces
            })

            print(f"画像 {os.path.basename(image_path)} の分析完了: {len(faces)}個の顔を検出")

        except Exception as e:
            print(f"警告: 画像 {image_path} の処理中にエラーが発生しました: {e}")

    # HTML生成
    output_path = generate_html(all_results, args.output)

    print(f"処理が完了しました。{len(all_results)}個の画像を分析しました。")
    print(f"結果は {output_path} に保存されました。")


def generate_html(image_results, output_path="emotion_analysis.html"):
    """
    感情分析結果をバーチャートで表示するHTMLを生成する

    Args:
        image_results (List[Dict]): 画像ごとの分析結果
        output_path (str): 出力するHTMLファイルのパス
    """
    # HTML テンプレート（純粋なHTMLとCSSを使用）
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>顔感情分析結果</title>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            h1 {{
                color: #333;
                text-align: center;
            }}
            .image-container {{
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 30px;
                padding: 20px;
            }}
            .image-info {{
                display: flex;
                flex-wrap: wrap;
                align-items: flex-start;
            }}
            .image-preview {{
                flex: 0 0 300px;
                margin-right: 20px;
                margin-bottom: 20px;
            }}
            .image-preview img {{
                max-width: 100%;
                border-radius: 4px;
                border: 1px solid #ddd;
            }}
            .emotions-container {{
                flex: 1;
                min-width: 300px;
            }}
            .emotion-bar {{
                margin-bottom: 8px;
            }}
            .emotion-label {{
                display: inline-block;
                width: 100px;
                font-weight: bold;
            }}
            .emotion-bar-container {{
                display: inline-block;
                width: calc(100% - 150px);
                background-color: #eee;
                height: 20px;
                border-radius: 4px;
                overflow: hidden;
            }}
            .emotion-bar-fill {{
                height: 100%;
                background-color: #4CAF50;
                border-radius: 4px;
            }}
            .emotion-value {{
                display: inline-block;
                width: 50px;
                text-align: right;
            }}
            .no-faces {{
                color: #999;
                font-style: italic;
            }}
            .face-container {{
                margin-bottom: 20px;
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 8px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>顔感情分析結果</h1>
            <div id="results-container">
                <!-- 画像ごとの結果がここに挿入される -->
                {image_results}
            </div>
        </div>
    </body>
    </html>
    """

    image_results_html = ""

    # 各画像の結果をHTMLに変換
    for i, result in enumerate(image_results):
        image_path = result["image_path"]
        faces = result["faces"]

        # 画像ごとのHTMLコンテナ
        image_container = f"""
        <div class="image-container">
            <h2>{os.path.basename(image_path)}</h2>
            <div class="image-info">
                <div class="image-preview">
                    <img src="file://{os.path.abspath(image_path)}" alt="Image Preview">
                </div>
                {generate_faces_html(faces, image_path, i)}
            </div>
        </div>
        """

        image_results_html += image_container

    # 最終的なHTMLを生成して保存
    final_html = html_template.format(image_results=image_results_html)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)

    print(f"HTMLレポートが生成されました: {output_path}")
    return output_path


def generate_faces_html(faces, image_path, image_index):
    """各顔の感情分析結果をHTMLバーチャートで表示するコンテンツを生成"""
    if not faces:
        return '<p class="no-faces">顔が検出されませんでした</p>'

    faces_html = '<div class="emotions-container">'

    for face_idx, face in enumerate(faces):
        emotions = face.get("emotions", [])

        face_html = '<div class="face-container">'

        # 各感情ごとにバーを作成
        for emotion in emotions:
            emotion_type = emotion.get("Type", "")
            confidence = emotion.get("Confidence", 0)

            # 感情ごとのバーチャート（HTMLとCSSのみ）
            emotion_bar = f"""
            <div class="emotion-bar">
                <span class="emotion-label">{emotion_type}</span>
                <div class="emotion-bar-container">
                    <div class="emotion-bar-fill" style="width: {confidence}%;"></div>
                </div>
                <span class="emotion-value">{confidence:.1f}%</span>
            </div>
            """

            face_html += emotion_bar

        face_html += '</div>'
        faces_html += face_html

    faces_html += '</div>'
    return faces_html


if __name__ == "__main__":
    main()
