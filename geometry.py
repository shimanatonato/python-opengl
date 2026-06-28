# 3D処理関数
import numpy as np

# 回転角から回転行列を生成
def create_rotmtx_from_arg(y,p,r):
    yaw=np.array([  # ヨー
        [np.cos(y),0,np.sin(y)],
        [0,1,0],
        [-np.sin(y),0,np.cos(y)]
    ])
    pitch=np.array([  # ピッチ
        [1,0,0],
        [0,np.cos(p),-np.sin(p)],
        [0,np.sin(p),np.cos(p)]
    ])
    roll=np.array([  # ロール
        [np.cos(r),-np.sin(r),0],
        [np.sin(r),np.cos(r),0],
        [0,0,1]
    ])
    return roll@pitch@yaw
# center中心にrotの回転を加えた回転行列を作成
def rot_around_matrix44(rot,center):
    rt=np.concatenate((rot,center.reshape((3,1))),axis=1)  # 回転+回転後の平行移動
    t_minus=np.diag(np.array([1,1,1,1]))  # 回転前の平行移動
    t_minus[:3,3]=-center[:]
    mtx=rt@t_minus  # 回転前の平行移動+回転+回転後の平行移動
    mtx_44=np.vstack([mtx, np.array([[0, 0, 0, 1]])])
    return mtx_44
# 拡大・縮小の行列の作成
def scale_matrix44(scale):
    mtx44=np.eye(4, dtype=np.float32)
    mtx44[0:3]*=scale
    return mtx44
# 投影行列の作成
def create_projection_matrix44(K_mtx, width, height, near, far):
    fx = K_mtx[0, 0]
    fy = K_mtx[1, 1]
    cx = K_mtx[0, 2]
    cy = K_mtx[1, 2]
    proj_mtx=np.array([
        [2*fx/width,  0,           (2*cx/width - 1),       0],
        [0,           2*fy/height, (1 - 2*cy/height),      0], # Yは反転
        [0,           0,           -(far+near)/(far-near), -2*far*near/(far-near)],
        [0,           0,           -1,                    0]
    ], dtype=np.float32)
    return proj_mtx
# ビュー行列の作成
def create_view_matrix44(Rt_mat):
    mtx_44=np.eye(4, dtype=np.float32)
    mtx_44[:3,:]=Rt_mat
    mtx_44[1,:]*=-1
    mtx_44[2,:]*=-1
    return mtx_44