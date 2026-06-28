# 映像の処理
# オプティカルフロー処理
# 動画・カメラ映像の読み込み
import numpy as np
import cv2,time
import multiprocessing,ctypes
import multiprocessing.sharedctypes
import config

# オプティカルフロー処理
class OpticalFlowPoint:  # 画像から動きの大きい点を求めるクラス
    move_size_exp=config.OPTFLOW_EXP  # 動きの大きさをe乗
    # eが大きいほど動きの大きい画素の影響が大きくなる
    move_size_min=config.OPTFLOW_MOVEMIN  # 動きの大きさの最低値
    move_pix_min=config.OPTFLOW_PIXMIN  # 条件を満たす画素数の最低値
    def __init__(self,size,scale):
        # 画素のインデックスを画像と同じ形の行列形式で用意する
        self.idxs_img=np.array([[[ix,iy] for ix in range(size[1]//scale)] for iy in range(size[0]//scale)])
        self.scale=scale
    def calcpoint(self,previmg,nextimg,tgt_before):
        # オプティカルフロー（それぞれの画素の移動ベクトル）の取得
        flow = cv2.calcOpticalFlowFarneback(previmg, nextimg, None,0.5,3,15,3,5,1.2,0)
        flow_norm=np.linalg.norm(flow,axis=2)  # 各画素の動きの大きさ
        region_ok=flow_norm>=self.move_size_min  # 動きの大きさが閾値以上の画素
        if np.sum(region_ok)>=self.move_pix_min:
            # 動きの大きさが閾値以上の画素数が一定以上
            flow_power=np.power(flow_norm[region_ok],self.move_size_exp)  # 動きの大きさをexp乗
            idx_ok=self.idxs_img[region_ok]
            # 動きの大きさのexp乗を重みとして、画素のインデックスを加重平均
            tgtx=np.average(idx_ok[:,0],weights=flow_power)*self.scale
            tgty=np.average(idx_ok[:,1],weights=flow_power)*self.scale
        else:
            # 動きの大きさが閾値以上の画素数が一定以下
            # 前のフレームの点の位置を引き継ぐ
            tgtx=tgt_before[0]
            tgty=tgt_before[1]
        return tgtx,tgty
    
# 映像の読み込み処理
class VideoCaptureWrapper:
    def __init__(self,source):
        capture = cv2.VideoCapture(source)  # ソース（動画、カメラ）を開く
        if not capture.isOpened():  # ソースが開けない
            raise IOError()
        _, mat = capture.read()
        self.shape=mat.shape
        height, width, channels=self.shape
        self.buffer = multiprocessing.sharedctypes.RawArray(
            ctypes.c_uint8, height * width * channels)  # 高速化のためバッファーを使用
        
        self.ready = multiprocessing.Event()  # 読み込みのイベント制御
        self.cancel = multiprocessing.Event()  # プロセス削除のイベント制御
        self.isread=multiprocessing.Event()  # フレーム読み込み済みのイベント制御
        self.enqueue = multiprocessing.Process(target=update, args=(
            source,self.buffer, self.ready, self.cancel,self.isread), daemon=True)  # 映像の更新
        self.enqueue.start()
        self.released = False  # プロセス削除済フラグ        
    def read(self):
        # 映像の読み込み
        self.ready.wait()  # 読み込めるまで待つ
        self.isread.set()  # 読み込み済み
        return True, np.reshape(self.buffer, self.shape).copy()
    def release(self):
        # クラス削除時にプロセス削除
        if self.released:
            return
        self.cancel.set()
        self.enqueue.join()
        self.released = True
    def __del__(self):  # デストラクタ
        try:
            self.release()
        except:
            pass
def update(source,buffer,ready,cancel,isread):
    # 毎フレームの映像読み込み処理
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise IOError()
    # 動画ファイルかどうか判定
    is_video = isinstance(source, str)
    if is_video:
        fps = capture.get(cv2.CAP_PROP_FPS)  # 動画の元のFPSを取得
        frame_delay = 1.0 / fps if fps > 0 else 1.0 / 30.0  # 1フレームに必要な秒数
    else:
        frame_delay = 0.0
    try:
        while not cancel.is_set():  # 読み込める間ループ
            t_start = time.time()
            ret, mat = capture.read()
            if not ret:
                if is_video:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            ready.clear()
            memoryview(buffer).cast('B')[:] = memoryview(mat).cast('B')[:]  # バッファにカメラ画像をコピー
            ready.set()
            isread.clear()
        
            if is_video:
                # 動画の場合（fps分-読み込みにかかった時間）待機
                t_elapsed = time.time() - t_start  # 読み込みとコピーにかかった時間
                wait_time = frame_delay - t_elapsed  # 残り時間
                if wait_time > 0:
                    time.sleep(wait_time)  # 足りない時間分だけスリープ
    finally:
        capture.release()