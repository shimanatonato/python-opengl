# ファイルの読み込み処理

import numpy as np

# OBJファイルを読み込み
def loadobj(filePath,mtldata):
    # 生データ格納用
    raw_positions = []
    raw_normals = []
    # 最終的なバッファ用
    vertices = []  # [x, y, z, nx, ny, nz, r, g, b] のリスト
    indices = []
    # 頂点の重複チェック用辞書
    # キー: (pos_idx, norm_idx, mat_id) → 値: 新しい頂点リストでのインデックス
    vertex_cache = {}

    current_material_color = [1.0, 1.0, 1.0] # デフォルトの色
    with open(filePath, 'r') as f:
        for line in f:
            tokens = line.split()
            if not tokens: continue
            if tokens[0] == 'v': # 頂点
                raw_positions.append([float(x) for x in tokens[1:4]])
            elif tokens[0] == 'vn': # 法線
                raw_normals.append([float(x) for x in tokens[1:4]])
            elif tokens[0] == 'usemtl': # マテリアル切り替え
                if tokens[1] in mtldata:
                    current_material_color = [mtldata[tokens[1]][i] for i in range(3)]
                else:
                    current_material_color = [0.8, 0.8, 0.8]
            elif tokens[0] == 'f': # 面 (v/vt/vn)
                for v_def in tokens[1:4]:
                    parts = v_def.split('/')
                    # 座標と法線のインデックス取得 (OBJは1-based index)
                    pos_idx = int(parts[0]) - 1
                    norm_idx = int(parts[2]) - 1 if len(parts) > 2 else -1
                    # キーの作成 
                    # 頂点を共有するポリゴンについて、色が同じなら同じ頂点、色が異なる場合別の頂点として扱う)
                    unique_key = (pos_idx, norm_idx, tuple(current_material_color))
                    if unique_key not in vertex_cache:
                        # 未登録なら新しい頂点として追加
                        new_idx = len(vertices) // 9 # 1頂点あたり9要素(位置3+法線3+色3)
                        vertex_cache[unique_key] = new_idx                        
                        # 頂点バッファにデータを詰める
                        vertices.extend(raw_positions[pos_idx])
                        if norm_idx != -1:
                            vertices.extend(raw_normals[norm_idx])
                        else:
                            vertices.extend([0, 0, 0]) # 法線がない場合
                        vertices.extend(current_material_color)
                        indices.append(new_idx)
                    else:
                        # 登録済みなら既存のインデックスを再利用
                        indices.append(vertex_cache[unique_key])
    # オブジェクトの大きさも出力（最適な大きさにスケーリングする倍率を求めるため）
    positions = np.array(raw_positions)
    min_pt = np.min(positions, axis=0) # [min_x, min_y, min_z]
    max_pt = np.max(positions, axis=0) # [max_x, max_y, max_z]
    size = max_pt - min_pt
    return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint32),size

# MTLファイルの読み込み
def loadmtl(filePath):
    mtldic={}
    reading=False
    nowmtl=""
    for line in open(filePath, "r"):
        vals = line.split()
        if len(vals) == 0:
            continue
        if vals[0] == "newmtl":
            nowmtl=vals[1]
            reading=True
        if vals[0]=="Kd" and reading:  # マテリアルの拡散反射色のみ取り出す
            mtldic[nowmtl]=(float(vals[1]),float(vals[2]),float(vals[3]))
            reading=False
    return mtldic