# 猫モデルの動きを制御
import numpy as np
import time
import geometry,config

# マウス位置を表す平面上の座標から視線方向のヨーとピッチを計算
def calc_watch_dir(pt1,vect,pt2):
    # vectを基準に、pt1からpt2を見る回転角
    yaw=np.arctan2(pt2[0]-pt1[0],pt2[2]-pt1[2])
    pitch=np.arctan2(pt2[1]-pt1[1],pt2[2]-pt1[2])
    yaw_vect=np.arctan2(vect[0],vect[2])
    pitch_vect=np.arctan2(vect[1],vect[2])
    return yaw-yaw_vect,pitch-pitch_vect

class CatController:
    def __init__(self):
        # 初期値の設定
        self.monitor_plane_pix_size=1  # モデルの注視平面の1画素あたりの大きさ
        self.height=400
        self.width=600
        self.scale=1
        self.scale_mtx=np.diag([1,1,1,1])
        self.offset_head_center=np.vstack([  # モデルの中心位置に基づく補正
                np.hstack((np.eye(3,dtype=np.float32),-config.HEAD_CENTER.reshape(3,1))),
                np.array([[0, 0, 0, 1]])
                ])
    def set_image_size(self,height,width):
        # 画像サイズを設定
        self.height=height
        self.width=width
        self.monitor_plane_pix_size=config.MONITOR_PLANE_WIDTH/self.width  # モデルの注視平面における1画素当たりの大きさ
    def set_head_scale(self,scale):
        # 頭の大きさを設定
        self.scale=scale
        self.scale_mtx=geometry.scale_matrix44(self.scale)
        self.left_eye_center=config.LEFT_EYE_CENTER*self.scale
        self.right_eye_center=config.RIGHT_EYE_CENTER*self.scale
    def calcRotate(self,headx,heady,eyex,eyey):
        # 回転を計算

        # 頭の回転
        headx_3d=(headx-self.width/2)*self.monitor_plane_pix_size  # 頭の注視する3次元座標
        heady_3d=(heady-self.height/2)*self.monitor_plane_pix_size
        o=np.zeros(3)
        hdir=calc_watch_dir(o,config.hvect,(headx_3d,heady_3d,config.CAMERA_POSITION[2]))  # 頭の回転角度
        head_rot_mtx=geometry.create_rotmtx_from_arg(hdir[0],-hdir[1],0)
        
        # 目の回転
        eyex_3d=(eyex-self.width/2)*self.monitor_plane_pix_size  # 目の注視する3次元座標
        eyey_3d=(eyey-self.height/2)*self.monitor_plane_pix_size
        left_center=head_rot_mtx@self.left_eye_center  # 左目の回転中心
        right_center=head_rot_mtx@self.right_eye_center  # 右目の回転中心
        left_dir=head_rot_mtx@config.hvect  # 左目の現在の向き
        right_dir=head_rot_mtx@config.hvect  # 右目の現在の向き
        ldir=calc_watch_dir(left_center,left_dir,(eyex_3d,eyey_3d,config.CAMERA_POSITION[2]))  # 左目の回転角度
        rdir=calc_watch_dir(right_center,right_dir,(eyex_3d,eyey_3d,config.CAMERA_POSITION[2]))  # 右目の回転角度

        # 回転
        head_rotmtx=geometry.rot_around_matrix44(head_rot_mtx,o)@self.scale_mtx@self.offset_head_center
        leye_rotmtx=geometry.rot_around_matrix44(geometry.create_rotmtx_from_arg(ldir[0],-ldir[1],0),left_center)@head_rotmtx
        reye_rotmtx=geometry.rot_around_matrix44(geometry.create_rotmtx_from_arg(rdir[0],-rdir[1],0),right_center)@head_rotmtx
        return [head_rotmtx,leye_rotmtx,reye_rotmtx]