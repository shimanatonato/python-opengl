# 猫モデルの動きを制御
import numpy as np
import time
import geometry,config

# マウス位置を表す平面上の座標に向かう視線方向のヨーとピッチを計算
def calc_watch_angle_rad(pt1,vect,pt2):
    # pt1からpt2を見る、vectを基準とした回転角
    yaw=np.arctan2(pt2[0]-pt1[0],pt2[2]-pt1[2])
    pitch=np.arctan2(pt2[1]-pt1[1],pt2[2]-pt1[2])
    yaw_vect=np.arctan2(vect[0],vect[2])
    pitch_vect=np.arctan2(vect[1],vect[2])
    return yaw-yaw_vect,pitch-pitch_vect

class CatController:
    def __init__(self):
        # 仮の初期値の設定
        self.monitor_plane_pix_size=1
        self.height=400
        self.width=600
        self.scale=1
        self.scale_mtx=np.diag([1,1,1,1]) 

        # 3d設定情報の読み込み
        # モデルの中心位置に基づく補正
        self.offset_head_center=np.vstack([
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
    def calcPose(self,headx,heady,eyex,eyey):
        # 頭と目の姿勢を計算

        # 頭の回転
        headx_3d=(headx-self.width/2)*self.monitor_plane_pix_size  # 頭の注視する3次元座標
        heady_3d=(heady-self.height/2)*self.monitor_plane_pix_size
        o=np.zeros(3)
        head_angle=calc_watch_angle_rad(o,config.hvect,(headx_3d,heady_3d,config.CAMERA_POSITION[2]))  # 頭の回転角度
        head_rot_mtx=geometry.create_rotmtx_from_angle_rad(head_angle[0],-head_angle[1],0)
        
        # 目の回転
        watchx_3d=(eyex-self.width/2)*self.monitor_plane_pix_size
        watchy_3d=(eyey-self.height/2)*self.monitor_plane_pix_size
        watch_pt_3d=(watchx_3d,watchy_3d,config.CAMERA_POSITION[2])  # 目の注視する3次元座標
        leye_center=head_rot_mtx@self.left_eye_center  # 左目の回転中心
        reye_center=head_rot_mtx@self.right_eye_center  # 右目の回転中心
        head_dir=head_rot_mtx@config.hvect  # 頭の現在の向き
        leye_angle=calc_watch_angle_rad(leye_center,head_dir,watch_pt_3d)  # 左目の回転角度
        reye_angle=calc_watch_angle_rad(reye_center,head_dir,watch_pt_3d)  # 右目の回転角度
        leye_rot_mtx=geometry.create_rotmtx_from_angle_rad(leye_angle[0],-leye_angle[1],0)
        reye_rot_mtx=geometry.create_rotmtx_from_angle_rad(reye_angle[0],-reye_angle[1],0)

        # 姿勢
        head_pose_mtx=geometry.rot_around_matrix44(head_rot_mtx,o)@self.scale_mtx@self.offset_head_center
        leye_pose_mtx=geometry.rot_around_matrix44(leye_rot_mtx,leye_center)@head_pose_mtx
        reye_pose_mtx=geometry.rot_around_matrix44(reye_rot_mtx,reye_center)@head_pose_mtx
        return [head_pose_mtx,leye_pose_mtx,reye_pose_mtx]