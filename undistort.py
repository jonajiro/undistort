import tkinter as tk            # ウィンドウ作成用
import tkinter.ttk as ttk
from tkinter import filedialog  # ファイルを開くダイアログ用
from PIL import Image, ImageTk  # 画像データ用
import numpy as np              # アフィン変換行列演算用
import os                       # ディレクトリ操作用
import cv2

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.pack()

        self.my_title = "歪曲収差除去"  # タイトル
        self.back_color = "#000000"     # 背景色

        # ウィンドウの設定
        self.master.title(self.my_title)    # タイトル
        self.master.geometry("1200x800")     # サイズ

        self.pil_image = None           # 表示する画像データ
        self.filename = None            # 最後に開いた画像ファイル名
        self.img_word = None
        self.img_worde = None

        self.undist_flg = 0

        self.prog_var = tk.IntVar()


        self.create_menu()   # メニューの作成
        self.create_widget() # ウィジェットの作成
    # -------------------------------------------------------------------------------
    # メニューイベント
    # -------------------------------------------------------------------------------
    def menu_open_clicked(self, event=None):
        # File → Open
        filename = tk.filedialog.askopenfilename(
            filetypes = [("Image file", ".bmp .png .jpg .tif"), ("Bitmap", ".bmp"), ("PNG", ".png"), ("JPEG", ".jpg"), ("Tiff", ".tif") ], # ファイルフィルタ
            initialdir = os.getcwd() # カレントディレクトリ
            )
        # 画像ファイルを設定する
        self.set_image(filename)
        self.prog_var.set(0)

    def menu_reload_clicked(self, event=None):
        # File → ReLoad
        self.set_image(self.filename)
        self.prog_var.set(0)

    def menu_quit_clicked(self):
        # ウィンドウを閉じる
        self.master.destroy()

    # -------------------------------------------------------------------------------

    # create_menuメソッドを定義
    def create_menu(self):
        self.menu_bar = tk.Menu(self) # Menuクラスからmenu_barインスタンスを生成

        self.file_menu = tk.Menu(self.menu_bar, tearoff = tk.OFF)
        # self.menu_bar.add_cascade(label="Video File", menu=self.file_menu)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

        self.file_menu.add_command(label="Image Open", command = self.menu_open_clicked, accelerator="Ctrl+O")
        self.file_menu.add_command(label="Image ReLoad", command = self.menu_reload_clicked, accelerator="Ctrl+R")
        self.file_menu.add_separator() # セパレーターを追加
        self.file_menu.add_command(label="Exit", command = self.menu_quit_clicked)

        self.menu_bar.bind_all("<Control-o>", self.menu_open_clicked) # ファイルを開くのショートカット(Ctrol-Oボタン)

        self.master.config(menu=self.menu_bar) # メニューバーの配置

    def create_widget(self):
        '''ウィジェットの作成'''

        #####################################################
        # ステータスバー相当(親に追加)
        self.statusbar = tk.Frame(self.master)
        self.mouse_position = tk.Label(self.statusbar, relief = tk.SUNKEN, text="mouse position") # マウスの座標
        self.image_position = tk.Label(self.statusbar, relief = tk.SUNKEN, text="image position") # 画像の座標
        self.label_space = tk.Label(self.statusbar, relief = tk.SUNKEN)                           # 隙間を埋めるだけ
        self.image_info = tk.Label(self.statusbar, relief = tk.SUNKEN, text="image info")         # 画像情報
        self.progbar = ttk.Progressbar(self.statusbar,mode="determinate",maximum = 100,variable=self.prog_var)
        self.prog_var.set(0)
        self.mouse_position.pack(side=tk.LEFT)
        self.image_position.pack(side=tk.LEFT)
        self.label_space.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.image_info.pack(side=tk.RIGHT)
        self.progbar.pack(side=tk.RIGHT)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        #####################################################
        # 右側フレーム（画像処理用ボタン配置用）
        right_frame = tk.Frame(self.master, relief = tk.SUNKEN, bd = 2, width = 600)
        # right_frame.propagate(False) # フーレムサイズの自動調整を無効にする


        lbl_intro0 = tk.Label(right_frame, text = "[File]→[Image Open]：画像選択")
        lbl_intro1 = tk.Label(right_frame, text = "[収差除去]：歪曲収差係数ファイル選択")


        # 歪曲収差計算
        self.btn_cal = tk.Button(right_frame, text = "収差除去", width = 15, command = self.btn_cal_click)

        lbl_intro0.grid(row = 0, column = 0, sticky=tk.EW)
        lbl_intro1.grid(row = 1, column = 0, sticky=tk.EW)
        self.btn_cal.grid(row = 3, column = 0, sticky=tk.EW)

        # フレームを配置
        right_frame.pack(side = tk.RIGHT, fill = tk.Y)


        #####################################################
        # Canvas(画像の表示用)
        self.canvas = tk.Canvas(self.master, background= self.back_color)
        self.canvas.pack(expand=True,  fill=tk.BOTH)  # この両方でDock.Fillと同じ

        #####################################################
        # マウスイベント
        self.canvas.bind("<Motion>", self.mouse_move)                       # MouseMove
        self.canvas.bind("<B1-Motion>", self.mouse_move_left)               # MouseMove（左ボタンを押しながら移動）
        self.canvas.bind("<Button-1>", self.mouse_down_left)                # MouseDown（左ボタン）
        self.canvas.bind("<Double-Button-1>", self.mouse_double_click_left) # MouseDoubleClick（左ボタン）
        self.canvas.bind("<MouseWheel>", self.mouse_wheel)                  # MouseWheel

        self.canvas.bind("<B3-Motion>", self.mouse_move_right)               # MouseMove（左ボタンを押しながら移動）
        self.canvas.bind("<Button-3>", self.mouse_down_right)                # MouseDown（左ボタン）
        self.canvas.bind("<ButtonRelease-3>", self.mouse_up_right)                # MouseDown（左ボタン）

    def set_image(self, filename):
        ''' 画像ファイルを開く '''
        if not filename or filename is None:
            return

        # 画像ファイルの再読込用に保持
        self.filename = filename

        # PIL.Imageで開く
        self.pil_image = Image.open(filename)

        # PillowからNumPy(OpenCVの画像)へ変換
        self.cv_image = np.array(self.pil_image)
        # カラー画像のときは、RGBからBGRへ変換する
        if self.cv_image.ndim == 3:
            self.cv_image = cv2.cvtColor(self.cv_image, cv2.COLOR_RGB2BGR)

        # 画像全体に表示するようにアフィン変換行列を設定
        self.zoom_fit(self.pil_image.width, self.pil_image.height)
        # 画像の表示
        self.draw_image(self.cv_image)

        # ウィンドウタイトルのファイル名を設定
        self.master.title(self.my_title + " - " + os.path.basename(filename))
        # ステータスバーに画像情報を表示する
        self.image_info["text"] = f"{self.pil_image.width} x {self.pil_image.height} {self.pil_image.mode}"
        # カレントディレクトリの設定
        os.chdir(os.path.dirname(filename))


    # -------------------------------------------------------------------------------
    # マウスイベント
    # -------------------------------------------------------------------------------

    def mouse_move(self, event):
        ''' マウスの移動時 '''
        # マウス座標
        self.mouse_position["text"] = f"mouse(x, y) = ({event.x: 4d}, {event.y: 4d})"

        if self.pil_image is None:
            return

        # 画像座標
        mouse_posi = np.array([event.x, event.y, 1]) # マウス座標(numpyのベクトル)
        mat_inv = np.linalg.inv(self.mat_affine)     # 逆行列（画像→Cancasの変換からCanvas→画像の変換へ）
        image_posi = np.dot(mat_inv, mouse_posi)     # 座標のアフィン変換
        x = int(np.floor(image_posi[0]))
        y = int(np.floor(image_posi[1]))
        if x >= 0 and x < self.pil_image.width and y >= 0 and y < self.pil_image.height:
            # 輝度値の取得
            value = self.pil_image.getpixel((x, y))
            self.image_position["text"] = f"image({x: 4d}, {y: 4d}) = {value}"
        else:
            self.image_position["text"] = "-------------------------"

    def mouse_move_left(self, event):
        ''' マウスの左ボタンをドラッグ '''
        if self.pil_image is None:
            return
        self.translate(event.x - self.__old_event.x, event.y - self.__old_event.y)
        self.redraw_image() # 再描画
        self.__old_event = event

    def mouse_down_left(self, event):
        ''' マウスの左ボタンを押した '''
        self.__old_event = event

    def mouse_down_right(self, event):
        ''' マウスの右ボタンを押した '''
        if self.pil_image is None:
            return

    def mouse_up_right(self, event):
        ''' マウスの右ボタンを離した '''
        if self.pil_image is None:
            return
        self.redraw_image() # 再描画

    def mouse_move_right(self, event):
        ''' マウスの右ボタンを押して動かした '''
        if self.pil_image is None:
            return


    def mouse_double_click_left(self, event):
        ''' マウスの左ボタンをダブルクリック '''
        if self.pil_image is None:
            return
        self.zoom_fit(self.pil_image.width, self.pil_image.height)
        self.redraw_image() # 再描画


    def mouse_wheel(self, event):
        ''' マウスホイールを回した '''
        if self.pil_image is None:
            return

        if (event.delta < 0):
            # 上に回転の場合、縮小
            self.scale_at(0.8, event.x, event.y)
        else:
            # 下に回転の場合、拡大
            self.scale_at(1.25, event.x, event.y)

        self.redraw_image() # 再描画

    # -------------------------------------------------------------------------------
    # 画像表示用アフィン変換
    # -------------------------------------------------------------------------------

    def reset_transform(self):
        '''アフィン変換を初期化（スケール１、移動なし）に戻す'''
        self.mat_affine = np.eye(3) # 3x3の単位行列


    def translate(self, offset_x, offset_y):
        ''' 平行移動 '''
        mat = np.eye(3) # 3x3の単位行列
        mat[0, 2] = float(offset_x)
        mat[1, 2] = float(offset_y)

        self.mat_affine = np.dot(mat, self.mat_affine)

    def scale(self, scale:float):
        ''' 拡大縮小 '''
        mat = np.eye(3) # 単位行列
        mat[0, 0] = scale
        mat[1, 1] = scale

        self.mat_affine = np.dot(mat, self.mat_affine)

    def scale_at(self, scale:float, cx:float, cy:float):
        ''' 座標(cx, cy)を中心に拡大縮小 '''

        # 原点へ移動
        self.translate(-cx, -cy)
        # 拡大縮小
        self.scale(scale)
        # 元に戻す
        self.translate(cx, cy)

    def zoom_fit(self, image_width, image_height):
        '''画像をウィジェット全体に表示させる'''

        # キャンバスのサイズ
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if (image_width * image_height <= 0) or (canvas_width * canvas_height <= 0):
            return

        # アフィン変換の初期化
        self.reset_transform()

        scale = 1.0
        offsetx = 0.0
        offsety = 0.0

        if (canvas_width * image_height) > (image_width * canvas_height):
            # ウィジェットが横長（画像を縦に合わせる）
            scale = canvas_height / image_height
            # あまり部分の半分を中央に寄せる
            offsetx = (canvas_width - image_width * scale) / 2
        else:
            # ウィジェットが縦長（画像を横に合わせる）
            scale = canvas_width / image_width
            # あまり部分の半分を中央に寄せる
            offsety = (canvas_height - image_height * scale) / 2

        # 拡大縮小
        self.scale(scale)
        # あまり部分を中央に寄せる
        self.translate(offsetx, offsety)

    # -------------------------------------------------------------------------------
    # 描画
    # -------------------------------------------------------------------------------

    def draw_image(self, cv_image):

        if cv_image is None:
            return

        self.re_image = cv_image.copy()#四角形描画用
        self.cv_image = cv_image        #オーバーレイ用のコピー


        if self.undist_flg == 1:
            self.re_image = self.undist_img.copy()

        self.canvas.delete("all")

        # キャンバスのサイズ
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # キャンバスから画像データへのアフィン変換行列を求める
        #（表示用アフィン変換行列の逆行列を求める）
        mat_inv = np.linalg.inv(self.mat_affine)

        # ndarray(OpenCV)からPillowへ変換
        # カラー画像のときは、BGRからRGBへ変換する
        if self.re_image.ndim == 3:
            self.re_image = cv2.cvtColor(self.re_image, cv2.COLOR_BGR2RGB)
        # NumPyからPillowへ変換
        self.pil_image = Image.fromarray(self.re_image)

        # PILの画像データをアフィン変換する
        dst = self.pil_image.transform(
                    (canvas_width, canvas_height),  # 出力サイズ
                    Image.Transform.AFFINE,         # アフィン変換
                    tuple(mat_inv.flatten()),       # アフィン変換行列（出力→入力への変換行列）を一次元のタプルへ変換
                    Image.Resampling.NEAREST,       # 補間方法、ニアレストネイバー
                    fillcolor= self.back_color
                    )

        # 表示用画像を保持
        self.image = ImageTk.PhotoImage(image=dst)

        # 画像の描画
        self.canvas.create_image(
                0, 0,               # 画像表示位置(左上の座標)
                anchor='nw',        # アンカー、左上が原点
                image=self.image    # 表示画像データ
                )

    def redraw_image(self):
        ''' 画像の再描画 '''
        if self.cv_image is None:
            return
        self.draw_image(self.cv_image)

    # -------------------------------------------------------------------------------
    # ボタンイベント（画像処理）
    # -------------------------------------------------------------------------------

    def scl_k1_coefscroll(self,event=None):
        '''th_binaryスケールがスクロールされたとき'''
        if self.pil_image is None:
            return
        self.redraw_image()
    def scl_k2_coefscroll(self,event=None):
        '''th_binaryスケールがスクロールされたとき'''
        if self.pil_image is None:
            return
        self.redraw_image()
    def scl_k3_coefscroll(self,event=None):
        '''th_binaryスケールがスクロールされたとき'''
        if self.pil_image is None:
            return
        self.redraw_image()
    def scl_k4_coefscroll(self,event=None):
        '''th_binaryスケールがスクロールされたとき'''
        if self.pil_image is None:
            return
        self.redraw_image()
    def btn_cal_click(self):
        if self.pil_image is None:
            return
        # File → Open
        filename = tk.filedialog.askopenfilename(
            filetypes = [("CSV file", ".csv")], # ファイルフィルタ
            initialdir = os.getcwd() # カレントディレクトリ
            )
 
        params = np.loadtxt(filename, delimiter=',')
        self.btn_cal["state"] = "disable"
        self.file_menu.entryconfig( 0, state="disable" )
        self.file_menu.entryconfig( 1, state="disable" )

        alp = 0.1
        ita_num = 100
        x_undist = np.zeros([self.cv_image.shape[0],self.cv_image.shape[1]])
        y_undist = np.zeros([self.cv_image.shape[0],self.cv_image.shape[1]])
        for j in range(self.cv_image.shape[1]):
            self.prog_var.set(int(j/(self.cv_image.shape[1]-1)*100))
            self.progbar.update()
            for k in range(self.cv_image.shape[0]):
                x = j - params[0]
                y = k - params[1]
                xe = x
                ye = y
                r = np.sqrt(xe**2 + ye**2)
                eps = 0.5

                for i in range(ita_num):
                    xe_b = xe
                    ye_b = ye
                    r = (1-alp) * r + alp * np.sqrt(xe**2 + ye**2)
                    xe = x*(1+params[4]*r**2+params[5]*r**4)/(1+params[2]*r**2+params[3]*r**4)
                    ye = y*(1+params[4]*r**2+params[5]*r**4)/(1+params[2]*r**2+params[3]*r**4)
                    if np.sqrt((xe-xe_b)**2+(ye-ye_b)**2) < eps:
                        break
                x_undist[k,j] = xe + params[0]
                y_undist[k,j] = ye + params[1]
        self.undist_img = self.cv_image.copy()
        for j in range(self.undist_img.shape[1]):
            for k in range(self.undist_img.shape[0]):
                if 0 <= int(x_undist[k,j]) < self.undist_img.shape[1] and 0 <= int(y_undist[k,j]) < self.undist_img.shape[0]:
                    self.undist_img[k,j,0] = self.cv_image[int(y_undist[k,j]),int(x_undist[k,j]),0]
                    self.undist_img[k,j,1] = self.cv_image[int(y_undist[k,j]),int(x_undist[k,j]),1]
                    self.undist_img[k,j,2] = self.cv_image[int(y_undist[k,j]),int(x_undist[k,j]),2]
                else:
                    self.undist_img[k,j,0] = 0
                    self.undist_img[k,j,1] = 0
                    self.undist_img[k,j,2] = 0
        
        self.undist_flg = 1
        self.btn_cal["state"] = "active"
        self.file_menu.entryconfig(0, state="active" )
        self.file_menu.entryconfig(1, state="active" )
        filename = filedialog.asksaveasfilename(title = "名前を付けて保存",
            filetypes = [("JPG", ".jpg"),("Bitmap", ".bmp")],
            initialdir = "./",
            defaultextension = "jpg")
        cv2.imwrite(filename, self.undist_img)
        self.redraw_image()

if __name__ == "__main__":
    root = tk.Tk()
    app = Application(master=root)
    app.mainloop()
