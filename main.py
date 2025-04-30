import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
import threading
import wave
import time
import os
import subprocess
import shutil
import pyaudio
import whisper

# アプリケーション設定
class AppConfig:
    WINDOW_TITLE = "PyDiscussAssister"
    WINDOW_SIZE = "600x500"
    RECORDS_DIR = "records"
    ICON_PATH = "icon.ico"
    
    # UI設定
    class UI:
        PADDING = "10"
        BUTTON_WIDTH = 15
        BUTTON_HEIGHT = 2
        TEXT_HEIGHT = 15
        TEXT_WIDTH = 50
        FONT_FAMILY = "Arial"
        FONT_SIZE = 10
        TITLE_FONT_SIZE = 12
        
        # 色設定
        RECORD_START_COLOR = "#4CAF50"
        RECORD_STOP_COLOR = "#f44336"
        TEXT_COLOR = "white"

    # エラーメッセージ
    class ErrorMessages:
        ICON_NOT_FOUND = "アイコンファイルが見つかりません"
        NO_AUDIO_FILE = "音声ファイルが選択されていません"
        FFMPEG_NOT_FOUND = "FFmpegがインストールされていないか、PATHに追加されていません。"
        TRANSCRIPTION_ERROR = "文字起こし中にエラーが発生しました: {}"
        SAVE_ERROR = "ファイルの保存中にエラーが発生しました: {}"
        DELETE_ERROR = "ファイルの削除中にエラーが発生しました: {}"
        NO_TRANSCRIPTION = "保存する文字起こし結果がありません"
        NO_FILE_TO_DELETE = "削除するファイルが選択されていません"

    # 成功メッセージ
    class SuccessMessages:
        FILE_SAVED = "ファイルを保存しました"
        FILE_DELETED = "ファイルを削除しました"
        ALL_RECORDS_DELETED = "全ての録音ファイルを削除しました"

    # 確認メッセージ
    class ConfirmMessages:
        DELETE_FILE = "本当にファイルを削除しますか？"
        DELETE_ALL_RECORDS = "本当に全ての録音ファイルを削除しますか？"


class AudioRecorder:
    
    #音声録音を管理するクラス
    
    def __init__(self):
        """AudioRecorderの初期化"""
        self.recording = False
        self.frames = []
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.p = pyaudio.PyAudio()
        os.makedirs(AppConfig.RECORDS_DIR, exist_ok=True)

    def start_recording(self):
        
        #録音を開始する
      
        self.recording = True
        self.frames = []
        self.stream = self.p.open(format=self.FORMAT,
                                channels=self.CHANNELS,
                                rate=self.RATE,
                                input=True,
                                frames_per_buffer=self.CHUNK)

        def record():
            while self.recording:
                self.frames.append(self.stream.read(self.CHUNK))

        self.recording_thread = threading.Thread(target=record)
        self.recording_thread.start()

    def stop_recording(self):
        
        #録音を停止し、WAVファイルとして保存する
  
        self.recording = False
        self.recording_thread.join()
        self.stream.stop_stream()
        self.stream.close()

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        record_dir = os.path.join(AppConfig.RECORDS_DIR, timestamp)
        os.makedirs(record_dir, exist_ok=True)

        filepath = os.path.join(record_dir, 'record.wav')
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(b''.join(self.frames))

        return filepath


class PyDiscussAssister:

    #音声録音と文字起こしを行うGUIアプリケーション

    
    def __init__(self, root):
        """
        PyDiscussAssisterの初期化
        
        Args:
            root (tk.Tk): メインウィンドウ
        """
        self.root = root
        self.root.title(AppConfig.WINDOW_TITLE)
        self.root.geometry(AppConfig.WINDOW_SIZE)
        self._set_icon()

        self.recorder = AudioRecorder()
        self.model = None
        self.transcription_result = None
        self.current_audio_file = None
        self.available_models = ["tiny", "base", "small", "medium", "large"]
        self.selected_model = tk.StringVar(value="medium")

        self._build_ui()

    def _set_icon(self):
        #アプリケーションのアイコンを設定する
        try:
            self.root.iconbitmap(AppConfig.ICON_PATH)
        except:
            messagebox.showwarning("警告", AppConfig.ErrorMessages.ICON_NOT_FOUND)

    def _build_ui(self):
        #メインUIを構築
        self.main_frame = ttk.Frame(self.root, padding=AppConfig.UI.PADDING)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self._build_record_ui()
        self._build_transcribe_ui()

    def _build_record_ui(self):
        #録音UIを構築
        frame = ttk.LabelFrame(self.main_frame, text="録音", padding=AppConfig.UI.PADDING)
        frame.pack(fill=tk.X, pady=5)

        header_frame = ttk.Frame(frame)
        header_frame.pack(fill=tk.X, pady=5)

        ttk.Button(header_frame, text="ファイルの全削除", command=self.clear_all_records).pack(side=tk.RIGHT, padx=5)

        self.record_button = tk.Button(
            frame,
            text="録音開始",
            command=self.toggle_recording,
            bg=AppConfig.UI.RECORD_START_COLOR,
            fg=AppConfig.UI.TEXT_COLOR,
            font=(AppConfig.UI.FONT_FAMILY, AppConfig.UI.TITLE_FONT_SIZE),
            width=AppConfig.UI.BUTTON_WIDTH,
            height=AppConfig.UI.BUTTON_HEIGHT
        )
        self.record_button.pack(pady=10)

        self.status_label = tk.Label(
            frame,
            text="準備完了",
            font=(AppConfig.UI.FONT_FAMILY, AppConfig.UI.FONT_SIZE)
        )
        self.status_label.pack(pady=5)

    def _build_transcribe_ui(self):
        #文字起こしUIを構築
        frame = ttk.LabelFrame(self.main_frame, text="文字起こし", padding=AppConfig.UI.PADDING)
        frame.pack(fill=tk.X, pady=5)

        model_frame = ttk.Frame(frame)
        model_frame.pack(fill=tk.X, pady=5)
        ttk.Label(model_frame, text="モデル:").pack(side=tk.LEFT, padx=5)
        model_combo = ttk.Combobox(model_frame, textvariable=self.selected_model, values=self.available_models, state="readonly")
        model_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(frame, text="音声ファイルを選択", command=self.select_file).pack(pady=5)
        self.file_path_label = ttk.Label(frame, text="選択されたファイル: なし")
        self.file_path_label.pack(pady=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=5)

        self.transcribe_button = ttk.Button(btn_frame, text="文字起こしを開始", command=self.transcribe, state=tk.DISABLED)
        self.transcribe_button.pack(side=tk.LEFT, padx=5)

        self.save_button = ttk.Button(btn_frame, text="テキストファイルに保存", command=self.save_to_file, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.delete_button = ttk.Button(btn_frame, text="ファイルを削除する", command=self.delete_file, state=tk.DISABLED)
        self.delete_button.pack(side=tk.LEFT, padx=10)

        self.result_text = tk.Text(frame, height=AppConfig.UI.TEXT_HEIGHT, width=AppConfig.UI.TEXT_WIDTH)
        self.result_text.pack(pady=5)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text['yscrollcommand'] = scrollbar.set

    def toggle_recording(self):
        #録音の開始/停止を切り替え
        if not self.recorder.recording:
            self.recorder.start_recording()
            self.record_button.config(text="録音停止", bg=AppConfig.UI.RECORD_STOP_COLOR)
            self.status_label.config(text="録音中...")
        else:
            self.current_audio_file = self.recorder.stop_recording()
            self.record_button.config(text="録音開始", bg=AppConfig.UI.RECORD_START_COLOR)
            self.status_label.config(text="録音完了")
            self.file_path_label.config(text=f"録音ファイル: {os.path.basename(self.current_audio_file)}")
            self.transcribe_button.config(state=tk.NORMAL)

    def select_file(self):
        #音声ファイルを選択
        file_path = filedialog.askopenfilename(
            title="音声ファイルを選択",
            filetypes=[("音声ファイル", "*.wav *.mp3 *.m4a")]
        )
        if file_path:
            self.current_audio_file = file_path
            self.file_path_label.config(text=f"選択されたファイル: {os.path.basename(file_path)}")
            self.transcribe_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.DISABLED)
            self.result_text.delete(1.0, tk.END)
            self.transcription_result = None

    def transcribe(self):
        """選択された音声ファイルを文字起こしする"""
        if not self.current_audio_file:
            messagebox.showerror("エラー", AppConfig.ErrorMessages.NO_AUDIO_FILE)
            return

        if not self._check_ffmpeg():
            messagebox.showerror("エラー", AppConfig.ErrorMessages.FFMPEG_NOT_FOUND)
            return

        try:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "文字起こしを実行しています...\n")
            self.root.update()

            selected_model = self.selected_model.get()
            self.model = whisper.load_model(selected_model)

            result = self.model.transcribe(self.current_audio_file)
            self.transcription_result = result["text"]
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, self.transcription_result)
            self.save_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("エラー", AppConfig.ErrorMessages.TRANSCRIPTION_ERROR.format(str(e)))

    def save_to_file(self):
        #文字起こし結果をファイルに保存
        if not self.transcription_result:
            messagebox.showerror("エラー", AppConfig.ErrorMessages.NO_TRANSCRIPTION)
            return

        default_filename = f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path = filedialog.asksaveasfilename(
            title="テキストファイルを保存",
            defaultextension=".txt",
            initialfile=default_filename,
            filetypes=[("テキストファイル", "*.txt")]
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.transcription_result)
                messagebox.showinfo("成功", AppConfig.SuccessMessages.FILE_SAVED)
            except Exception as e:
                messagebox.showerror("エラー", AppConfig.ErrorMessages.SAVE_ERROR.format(str(e)))

    def delete_file(self):
        #選択されたファイルを削除
        if not self.current_audio_file:
            messagebox.showerror("エラー", AppConfig.ErrorMessages.NO_FILE_TO_DELETE)
            return

        if messagebox.askyesno("確認", AppConfig.ConfirmMessages.DELETE_FILE):
            try:
                target_dir = os.path.dirname(self.current_audio_file)
                if os.path.exists(self.current_audio_file):
                    os.remove(self.current_audio_file)
                if not os.listdir(target_dir):
                    os.rmdir(target_dir)

                self.current_audio_file = None
                self.file_path_label.config(text="選択されたファイル: なし")
                self.transcribe_button.config(state=tk.DISABLED)
                self.save_button.config(state=tk.DISABLED)
                self.result_text.delete(1.0, tk.END)
                self.transcription_result = None

                messagebox.showinfo("成功", AppConfig.SuccessMessages.FILE_DELETED)
            except Exception as e:
                messagebox.showerror("エラー", AppConfig.ErrorMessages.DELETE_ERROR.format(str(e)))

    def clear_all_records(self):
        #全ての録音ファイルを削除
        if messagebox.askyesno("確認", AppConfig.ConfirmMessages.DELETE_ALL_RECORDS):
            try:
                shutil.rmtree(AppConfig.RECORDS_DIR, ignore_errors=True)
                os.mkdir(AppConfig.RECORDS_DIR)
                messagebox.showinfo("成功", AppConfig.SuccessMessages.ALL_RECORDS_DELETED)
            except Exception as e:
                messagebox.showerror("エラー", AppConfig.ErrorMessages.DELETE_ERROR.format(str(e)))

    def _check_ffmpeg(self):
        #FFmpegが利用可能かチェック
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except FileNotFoundError:
            return False


if __name__ == "__main__":
    root = tk.Tk()
    app = PyDiscussAssister(root)
    root.mainloop()