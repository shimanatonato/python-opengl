# 3D描画処理
# Zバッファー法で表示

import glfw,cv2
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import numpy as np
import geometry

# オブジェクトの頂点シェーダー
vertex_src = """
#version 330 core
layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_normal;
layout(location = 2) in vec3 a_color;

uniform mat4 u_projection;
uniform mat4 u_view;
uniform mat4 u_model;

out vec3 v_normal;
out vec3 v_color;

void main() {
    gl_Position = u_projection * u_view * u_model * vec4(a_position, 1.0);
    v_normal = mat3(transpose(inverse(u_model))) * a_normal;
    v_color = a_color;
}
"""
# オブジェクトのフラグメントシェーダー（単純なZバッファ法）
fragment_src = """
#version 330 core
in vec3 v_color;
out vec4 out_color;
void main() {
    out_color = vec4(v_color, 1.0);
}
"""
# 背景の頂点シェーダー
vertex_bg_src = """
#version 330 core
layout(location = 0) in vec2 a_pos;
layout(location = 1) in vec2 a_tex;
out vec2 v_tex;
void main() {
    v_tex = a_tex;
    gl_Position = vec4(a_pos, 0.0, 1.0); // Z=0.0で画面いっぱいに配置
}
"""
# 背景のフラグメントシェーダー
fragment_bg_src = """
#version 330 core
in vec2 v_tex;
uniform sampler2D u_texture;
out vec4 out_color;
void main() {
    out_color = texture(u_texture, v_tex);
}
"""

# OpenGLを使用するクラス
class ZBufferRenderer():
    # ウィンドウなどの設定
    def setting(self,size,visibility=True):  # 引数：ウィンドウサイズ、ウィンドウの可視性
        if not glfw.init():
            return
        self.WIDTH, self.HEIGHT = size
        if not visibility:  # OpenCVなどほかのウィンドウで表示する場合にOpenGL側のウィンドウを非表示
            glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        self.window = glfw.create_window(self.WIDTH, self.HEIGHT, "Zバッファ法", None, None)
        glfw.make_context_current(self.window)  # コンテキストを作成してウィンドウをメインに

        # Zバッファ（深度テスト）の有効化
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)

        self.settting_background()  # 背景の設定

        self.shader = compileProgram(compileShader(vertex_src, GL_VERTEX_SHADER),  # オブジェクト用のシェーダー設定
                                compileShader(fragment_src, GL_FRAGMENT_SHADER))
        # 座標変換行列の設定
        # P: 投影行列 (Projection) - 画面への映り方
        # V: ビュー行列 (View) - カメラの位置と向き
        # M: モデル行列 (Model) - 各物体の配置
        self.proj_loc = glGetUniformLocation(self.shader, "u_projection")
        self.view_loc = glGetUniformLocation(self.shader, "u_view")
        self.model_loc = glGetUniformLocation(self.shader, "u_model")
    # 背景の設定
    def settting_background(self):
        # 背景用テクスチャの作成
        self.bg_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.bg_texture)
        # パラメータ設定
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        # 枠線の設定
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

        # 板ポリゴンのVAO/VBO作成
        # VAO：VBO・EBOなどの設定
        # VBO：頂点・色などのデータ
        # EBO：要素のつなぎ順
        # [x, y, u, v]
        vertices = np.array([
            -1.0, -1.0,  0.0, 1.0,
            1.0, -1.0,  1.0, 1.0,
            -1.0,  1.0,  0.0, 0.0,
            1.0,  1.0,  1.0, 0.0
        ], dtype=np.float32)
        self.bg_vao = glGenVertexArrays(1)
        self.bg_vbo = glGenBuffers(1)
        glBindVertexArray(self.bg_vao)  # VAOをバインドして設定開始
        glBindBuffer(GL_ARRAY_BUFFER, self.bg_vbo)  # VBOをバインド
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)  # VBOに頂点情報をコピー
        
        # 座標属性 (location=0)
        glEnableVertexAttribArray(0)  # GPUへのポートを有効化
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(0))  # ポートとデータの区切りを設定
        # テクスチャ属性 (location=1)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(8))
        self.bgshader = compileProgram(compileShader(vertex_bg_src, GL_VERTEX_SHADER),   # 背景のシェーダー設定
                                compileShader(fragment_bg_src, GL_FRAGMENT_SHADER))
        glBindVertexArray(0)  # VAOをアンバインド
    # 物体を追加
    def add_obj(self,objDataList):
        len_obj=len(objDataList)
        self.objects = []
        size_list=[]
        for i in range(len_obj):
            vertices,indices,size=objDataList[i]
            size_list.append(size)
            # VAO/VBO/EBO作成
            # VAO（Vertex Array Object）：VBO・EBOなどの設定
            # VBO（Vertex Buffer Object）：頂点・色などのデータ
            # EBO（Element Buffer Object）：要素のつなぎ順
            VAO = glGenVertexArrays(1)
            VBO = glGenBuffers(1)
            EBO = glGenBuffers(1)
            glBindVertexArray(VAO)  # VAOをバインドして設定開始
            # VBOの設定
            glBindBuffer(GL_ARRAY_BUFFER, VBO)  # VBOをバインド
            glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)  # VBOに頂点情報をコピー
            # EBOの設定
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO)  # EBOをバインド
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)  # EBOにポリゴン情報をコピー

            # 座標属性 (location=0)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 36, ctypes.c_void_p(0))  # ポートとデータの区切りを設定
            glEnableVertexAttribArray(0)  # GPUへのポートを有効化
            # 法線属性 (location=1)
            glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 36, ctypes.c_void_p(12))
            glEnableVertexAttribArray(1)
            # 色属性 (location=2)
            glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, 36, ctypes.c_void_p(24))
            glEnableVertexAttribArray(2)

            glBindVertexArray(0)  # VAOをアンバインド

            self.objects.append({
                "vao": VAO, 
                "vbo": VBO,
                "ebo": EBO,
                "vertices":vertices,
                "indices":indices,
                "count": len(indices),
                "pos": [0, 0, 0]
            })
        return size_list  # オブジェクトの大きさを返す
    # カメラの設定
    def set_camera(self,K_mtx,Rt_mtx,near,far):
        self.projection=geometry.create_projection_matrix44(K_mtx,self.WIDTH,self.HEIGHT,near,far)
        self.view=geometry.create_view_matrix44(Rt_mtx)
    # 描画
    def draw_scene(self,background,models):
            glfw.poll_events()            
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1) # GPUへ送る時(背景画像)の設定を1バイト単位に変更
            glPixelStorei(GL_PACK_ALIGNMENT, 1)   # GPUから戻す時(glReadPixels)の設定を1バイト単位に変更
            glBindTexture(GL_TEXTURE_2D, self.bg_texture)  # テクスチャをバインド
            # OpenCV(BGR) をそのままOpenGLに送る
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.WIDTH, self.HEIGHT, 0, GL_BGR, GL_UNSIGNED_BYTE, background)
            # カラーバッファと深度バッファを両方クリアする
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            # 背景の描画
            glDisable(GL_DEPTH_TEST) # 深度テストをオフにして、必ず一番奥に描かれるようにする
            glUseProgram(self.bgshader)
            glBindVertexArray(self.bg_vao)
            glDisableVertexAttribArray(2)  # 背景はLocation0,1しか使わないのでLocation2が生きていたら消す
            glBindTexture(GL_TEXTURE_2D, self.bg_texture)
            glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
            glBindVertexArray(0) # アンバインド

            # 3Dオブジェクトの描画
            glEnable(GL_DEPTH_TEST) # 3D描画のために深度テストをオンに戻す
            glUseProgram(self.shader)
            glUniformMatrix4fv(self.proj_loc, 1, GL_TRUE, self.projection)
            glUniformMatrix4fv(self.view_loc, 1, GL_TRUE, self.view)

            # 各オブジェクトに入力したモデル行列を適応
            for i,obj in enumerate(self.objects):
                model=models[i]
                glUniformMatrix4fv(self.model_loc, 1, GL_TRUE, model)
                glEnableVertexAttribArray(2)
                glBindVertexArray(obj["vao"])
                glDrawElements(GL_TRIANGLES, obj["count"], GL_UNSIGNED_INT, None)

            glfw.swap_buffers(self.window)  # 描画内容をウィンドウに反映
            # 画像として出力する
            image_buffer = glReadPixels(0, 0, self.WIDTH, self.HEIGHT, GL_RGBA, GL_UNSIGNED_BYTE)
            image = np.frombuffer(image_buffer, dtype=np.uint8).reshape(self.HEIGHT, self.WIDTH, 4)
            image = cv2.flip(cv2.cvtColor(image, cv2.COLOR_RGBA2BGRA), 0)
            return image
    # ループが終了したら、リソースをクリーンアップ
    def clear_resourse(self):
        for obj in self.objects:
            glDeleteVertexArrays(1, [obj["vao"]])
            glDeleteBuffers(1, [obj["vbo"]])
            glDeleteBuffers(1, [obj["ebo"]])
        glDeleteVertexArrays(1, [self.bg_vao])
        glDeleteVertexArrays(1, [self.bg_vbo])
        glDeleteTextures(1, [self.bg_texture])
        glDeleteProgram(self.shader)
        glDeleteProgram(self.bgshader)
        glfw.terminate()