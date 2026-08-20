# ゲーム部分の担当
# 猫モデルの視線を誘導する目標ターゲットの設定
# 視線がターゲットにたどり着いたかの判定
import random
import cv2
import numpy as np
import config

class TargetCircle:
    # パラメータ設定
    r_min=config.TARGET_RADIUS_MIN  # ターゲットの半径の最大値（画像サイズの短辺に対する比）
    r_max=config.TARGET_RADIUS_MAX  # ターゲットの半径の最小値（画像サイズの短辺に対する比）
    color=config.TARGET_COLOR  # ターゲットの色（通常時）
    color_clear=config.TARGET_COLOR_CLEARED  # ターゲットの色（到達時）
    alpha=config.TARGET_ALPHA  # ターゲットの透明度（到達時）

    def __init__(self):
        # 初期値の設定
        self.cx = 0
        self.cy = 0
        self.radius = 0
        self.is_cleared = False
    def spawn(self, img_shape, x=None, y=None, r=None):
        # ターゲットの生成
        # x,y: 位置指定（指定のない場合画像内でランダム）
        # r: 半径指定（指定のない場合パラメータの設定範囲内でランダム）
        height,width,_ = img_shape
        self.is_cleared = False
        # 指定のない場合位置・サイズはランダム
        self.cx = random.randint(0, width - 1) if x is None else x
        self.cy = random.randint(0, height - 1) if y is None else y
        if r is None:
            short_side=min(height,width)
            r_min_real=int(self.r_min*short_side)
            r_max_real=int(self.r_max*short_side)
            self.radius=random.randint(max(r_min_real,0), min(r_max_real,short_side-1))
        else:
            self.radius=r
            
    def draw(self, img):
        # 描画
        result = img.copy()
        height, width, _ = result.shape
        r = self.radius

        # 描画対象のバウンディングボックス
        x1 = max(0, self.cx-r)
        y1 = max(0, self.cy-r)
        x2 = min(width, self.cx+r+1)
        y2 = min(height, self.cy+r+1)
        if x1 >= x2 or y1 >= y2:
            return result

        # 描画範囲の切り出し
        roi = result[y1:y2, x1:x2]
        overlay = roi.copy()

        # 範囲内の相対座標で円を描画
        target_color = self.color_clear if self.is_cleared else self.color
        local_center = (self.cx-x1, self.cy-y1)
        cv2.circle(overlay, local_center, self.radius, target_color, -1)

        # 描画範囲のみアルファブレンド
        result[y1:y2, x1:x2] = cv2.addWeighted(overlay, self.alpha, roi, 1-self.alpha, 0)
        return result
    def is_inside_of_circle(self,x,y):
        # ターゲット到達判定
        d=(self.cx-x)**2+(self.cy-y)**2  # ターゲット中心からの距離
        return self.radius**2>=d