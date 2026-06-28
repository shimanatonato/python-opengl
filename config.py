# パラメータの設定
import numpy as np

# デフォルト値
VIDEO_SOURCE_DEFAULT="source/video_default.mp4"  # 動画ファイルのパス
MODE_DEFAULT=0  # 動作モード（0:デフォルトの動画を読み込み, 1:カメラを起動, 2:マウス操作）
WIDTH_DEFAULT=600  # 画像サイズ
HEIGHT_DEFAULT=400
CAMERA_NUMBER=0  # 起動するカメラ

# 3D関連
# 座標系: X+右, Y+下, Z+奥
CAMERA_POSITION=np.array([0,0,-1000])  # カメラ位置
CAMERA_HPR=np.radians(np.array([0,0,0]))  # カメラの回転（ヨー・ピッチ・ロール）
FOCAL=35  # 焦点距離(単位：mm)
PIXEL_WIDTH=3.45/1000*4  # 画素のサイズ
MONITOR_PLANE_WIDTH=1000  # モデルが注目する平面の横幅

# モデルの設定
FINAL_HEAD_WIDTH=150  # モデルの横幅
HEAD_SPEED=1  # 頭の動く速度（カーソルに追いつくまでの秒数の逆数）
EYE_SPEED=3  # 目の動く速度

# モデルの情報
# 頭の回転の中心点（blender上の表示：[0, 0.58073, 0.65492]）
HEAD_CENTER=np.array([0, -0.65492, 0.58073])
# 左目の回転の中心点（blender上の表示：[0.498315, -0.069373, 0.65302]）
LEFT_EYE_CENTER=np.array([0.498315, -0.65302, -0.069373])-HEAD_CENTER
# 右目の回転の中心点（blender上の表示：[-0.498315, -0.069373, 0.65302]）
RIGHT_EYE_CENTER=np.array([-0.498315, -0.65302, -0.069373])-HEAD_CENTER
hvect=np.array([0,0,-1])  # 顔のデフォルトの向き    
OBJECT_SOURCE=["source/cat_head","source/cat_leye","source/cat_reye"]  # objファイル、mtlファイルのパス

# オプティカルフローの設定
OPTFLOW_SCALE=4  # オプティカルフロー計算時の画質調整（1で元の画像サイズ）
OPTFLOW_EXP=8  # 動きの大きさの指数
OPTFLOW_MOVEMIN=3  # 動きの大きさの最低値
OPTFLOW_PIXMIN=1000/OPTFLOW_SCALE  # 条件を満たす画素数の最低値