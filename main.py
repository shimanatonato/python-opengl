import numpy as np
import cv2,time,os,sys,multiprocessing
import draw3D_GL,cat_controller,config,vision,geometry,load_file

# exe化のための絶対パス取得関数
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstallerが作成する一時フォルダのパス
    except Exception:
        base_path = os.path.abspath(".")  # 通常実行時はスクリプトの場所
    return os.path.join(base_path, relative_path)

# マウス位置の取得
class MouseEvent:
    def __init__(self):
        self.x=self.y=0
    def on_mouse_move(self,e,x, y, flags, param):
        if e==cv2.EVENT_MOUSEMOVE:
            self.x=x
            self.y=y

def main():
    # モードの選択
    mode=config.MODE_DEFAULT
    while True:
        print("モードを入力してください（0:デフォルトの動画を読み込み, 1:カメラを起動, 2:マウス操作）")
        mode_str=input()
        if mode_str in ["0","1","2"]:
            mode=int(mode_str)
            break
        else:
            print("0, 1, 2以外を入力しないでください")
    video_source=-1
    if mode==0:
        video_source=resource_path(config.VIDEO_SOURCE_DEFAULT)
    elif mode==1:
        video_source=config.CAMERA_NUMBER
    capture=None
    mouse_event=None
    mode_video=False  # 動画・カメラ映像
    mode_mouse=False  # ダミー背景でマウス動作
    wname="window"
    cv2.namedWindow(wname)
    if mode==0 or mode==1:
        try:
            capture = vision.VideoCaptureWrapper(video_source)
        except IOError:
            print("\n" + "="*50)
            if mode == 1:
                print("【エラー】カメラを起動できませんでした。")
                print("・カメラが正しくパソコンに接続されているか確認してください。")
                print("・config.py の CAMERA_NUMBER が正しいか確認してください。")
                print("・他のアプリがカメラを占有していないか確認してください。")
            elif mode == 0:
                print("【エラー】デフォルトの動画ファイルを開けませんでした。")
                print("・config.py の VIDEO_SOURCE_DEFAULT に指定されたパスに動画ファイルが存在するか確認してください。")
            print("="*50 + "\n")
            cv2.destroyAllWindows()
            
            input("Enterキーを押すとプログラムを終了します...")
            sys.exit()  # プログラムを安全に終了させる
        mode_video=True
    elif mode==2:
        mouse_event=MouseEvent()
        cv2.setMouseCallback(wname, mouse_event.on_mouse_move)
        mode_mouse=True

    # カメラパラメータ計算
    R=geometry.create_rotmtx_from_arg(*config.CAMERA_HPR)  # カメラ回転行列
    t=-R@config.CAMERA_POSITION  # カメラ平行移動
    Rt_mtx=np.concatenate((R,t.reshape((3,1))),axis=1)  # カメラ外部パラメータ
    focal_px=config.FOCAL/config.PIXEL_WIDTH  # 画素サイズ[px]
    
    # 初期値の設定
    previmg_gray = None  # 前フレームの画像
    nextimg = None  # 今フレームの画像
    time_before=time.time()  # 前フレームの時刻
    time_now=time_before  # 今フレームの時刻
    time_diff=0  # 前のフレームからかかった時間
    target_px_before=[0,0]  # 前のフレームの注目画素
    head_px_before=[0,0]  # 前のフレームの頭の注目画素
    eye_px_before=[0,0]  # 前のフレームの目の注目画素
    time_sum=0  # フレーム当たりの秒数の合計（fpsの計算に使用）
    frame_sum=0  # 経過フレーム数

    # インスタンス化
    zbuffer_renderer=draw3D_GL.ZBufferRenderer()
    controller=cat_controller.CatController()
    
    print("ESCキーで終了します")
    
    # メインループ
    while True:
        tgtx,tgty=0,0  # 今フレームの注目画素
        is_new_frame = False  # 画像を読み込んだか
        if mode_video:
            if capture is not None and not capture.isread.is_set():
                _, nextimg = capture.read()  # 画像の読み込み
                # nextimg=cv2.resize(nextimg,None,fx=0.5,fy=0.5)  # 画質の調節
                if mode==1 and nextimg is not None:
                    nextimg = cv2.flip(nextimg, 1)  # インカメラ用の反転
                is_new_frame = True
        elif mode_mouse:
            if mouse_event is not None:
                nextimg = np.full((config.HEIGHT_DEFAULT,config.WIDTH_DEFAULT,3),255,dtype=np.uint8)  # ダミー画像
                is_new_frame = True
        if nextimg is not None:
            # 画像読み込み開始後
            height, width, _ = nextimg.shape
            
            if previmg_gray is None:  # 最初のフレームの場合
                optical_flow_point=vision.OpticalFlowPoint((height,width),config.OPTFLOW_SCALE)  #オプティカルフロー計算クラスのインスタンス化
                K_mtx=np.array([  # 内部パラメータ行列
                    [focal_px,0,width/2],
                    [0,focal_px,height/2],
                    [0,0,1]
                ])
                controller.set_image_size(height,width)
                target_px_before[0]=head_px_before[0]=eye_px_before[0]=width//2  # 前のフレームの注目画素
                target_px_before[1]=head_px_before[1]=eye_px_before[1]=height//2
                
                # GLFWの設定
                zbuffer_renderer.setting((width,height),visibility=False)   # ウィンドウ設定
                object_list=[]
                for path in config.OBJECT_SOURCE:
                    obj_src=resource_path(path+".obj")
                    mtl_src=resource_path(path+".mtl")
                    mtl_data=load_file.loadmtl(mtl_src)  # mtlファイルを読み込み
                    vertices,indices,size=load_file.loadobj(obj_src,mtl_data)  # objファイルを読み込み
                    object_list.append([vertices,indices,size])
                size_list=zbuffer_renderer.add_obj(object_list)  # オブジェクトの設定
                zbuffer_renderer.set_camera(K_mtx,Rt_mtx,900,1100)  # カメラの設定（内部パラメータ行列、外部パラメータ行列、描画範囲）

                scale=config.FINAL_HEAD_WIDTH/size_list[0][0]  # オブジェクトの大きさの調節
                controller.set_head_scale(scale)
            if mode_video:
                if is_new_frame:
                    #オプティカルフローの計算
                    nextimg_gray = cv2.resize(cv2.cvtColor(nextimg, cv2.COLOR_BGR2GRAY),None,fx=1/config.OPTFLOW_SCALE,fy=1/config.OPTFLOW_SCALE)
                    previmg_gray = nextimg_gray if previmg_gray is None else previmg_gray
                    # オプティカルフローから注目画素を決定
                    optx,opty=optical_flow_point.calcpoint(previmg_gray,nextimg_gray,target_px_before)
                    
                    if np.isnan(optx) or np.isnan(opty):
                        # NaNの場合
                        tgtx, tgty = target_px_before
                    else:
                        previmg_gray = nextimg_gray
                        tgtx, tgty = optx, opty
                else:
                    tgtx, tgty = target_px_before
            elif mode_mouse:
                # マウス座標を注目画素に代入
                tgtx,tgty=mouse_event.x,mouse_event.y
                previmg_gray=nextimg
        else:
            continue

        drawimg = nextimg.copy()  # 描画画像

        # 注目画素の計算
        # 設定速度に応じて徐々に追いかける
        headx=head_px_before[0]+(tgtx-head_px_before[0])*time_diff*config.HEAD_SPEED  # 頭の注目画素
        heady=head_px_before[1]+(tgty-head_px_before[1])*time_diff*config.HEAD_SPEED
        eyex=eye_px_before[0]+(tgtx-eye_px_before[0])*time_diff*config.EYE_SPEED  # 目の注目画素（左右同じ）
        eyey=eye_px_before[1]+(tgty-eye_px_before[1])*time_diff*config.EYE_SPEED
        
        rot_mtx_list=controller.calcRotate(headx,heady,eyex,eyey)
        # 描画
        drawimg=zbuffer_renderer.draw_scene(drawimg,rot_mtx_list)
        cv2.circle(drawimg,[int(tgtx),int(tgty)],10,(0,0,255),-1)  # 注目画素（移動の大きい画素）の表示
        cv2.imshow(wname, drawimg)  # 画像表示

        # 今フレームの情報の記録
        time_now=time.time()  # 今フレームの時刻
        time_diff=time_now-time_before  # 前のフレームからかかった時間
        time_before=time_now  # 今フレームの時刻
        target_px_before=[tgtx,tgty]  # 今フレームの注目画素
        head_px_before=[headx,heady]  # 今フレームの頭の注目画素
        eye_px_before=[eyex,eyey]  # 今フレームの目の注目画素
        time_sum+=time_diff
        frame_sum+=1
        if frame_sum!=0:
            print('\rfps : %f' % (frame_sum/time_sum), end='')  # fpsの表示

        # キー入力
        key = cv2.waitKey(1) & 0xFF
        if key == 0x1B:
            break
    if capture is not None:
        capture.release()
    zbuffer_renderer.clear_resourse()
    cv2.destroyAllWindows()
if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
    