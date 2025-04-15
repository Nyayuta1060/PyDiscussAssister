import tkinter as tk
import pyaudio
import wave
import threading
import time
import os
import subprocess
import whisper
from datetime import datetime
from tkinter import filedialog, messagebox, ttk


class AudioRecorder:
    def __init__(self):
        self.recording = False
        self.frames = []
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.p = pyaudio.PyAudio()
        
        # recordsフォルダが存在しない場合は作成
        if not os.path.exists('records'):
            os.makedirs('records')

    def start_recording(self):
        self.recording = True
        self.frames = []
        self.stream = self.p.open(format=self.FORMAT,
                                channels=self.CHANNELS,
                                rate=self.RATE,
                                input=True,
                                frames_per_buffer=self.CHUNK)
        
        def record():
            while self.recording:
                data = self.stream.read(self.CHUNK)
                self.frames.append(data)

        self.recording_thread = threading.Thread(target=record)
        self.recording_thread.start()

    def stop_recording(self):
        self.recording = False
        self.recording_thread.join()
        self.stream.stop_stream()
        self.stream.close()
        
        # フォルダを作成
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        record_dir = os.path.join('records', current_time)
        os.makedirs(record_dir, exist_ok=True)
        
        # 録音ファイルを保存
        filename = os.path.join(record_dir, 'record.wav')
        
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        
        return filename

class PyDiscussAssister:
    def __init__(self, root):
        self.root = root
        self.root.title("PyDiscussAssister")
        self.root.geometry("600x500")
        
        self.recorder = AudioRecorder()
        self.model = None
        self.transcription_result = None
        self.current_audio_file = None
        
        # メインフレーム
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 録音セクション
        self.record_frame = ttk.LabelFrame(self.main_frame, text="録音", padding="10")
        self.record_frame.pack(fill=tk.X, pady=5)
        
        self.record_button = tk.Button(self.record_frame, 
                                     text="録音開始", 
                                     command=self.toggle_recording,
                                     bg='#4CAF50',
                                     fg='white',
                                     font=('Arial', 12),
                                     width=15,
                                     height=2)
        self.record_button.pack(pady=10)
        
        self.status_label = tk.Label(self.record_frame, 
                                   text="準備完了", 
                                   font=('Arial', 10))
        self.status_label.pack(pady=5)
        
        # 文字起こしセクション
        self.transcribe_frame = ttk.LabelFrame(self.main_frame, text="文字起こし", padding="10")
        self.transcribe_frame.pack(fill=tk.X, pady=5)
        
        # ファイル選択ボタン
        self.select_button = ttk.Button(self.transcribe_frame, 
                                      text="音声ファイルを選択", 
                                      command=self.select_file)
        self.select_button.pack(pady=5)
        
        # ファイルパス表示
        self.file_path_label = ttk.Label(self.transcribe_frame, 
                                       text="選択されたファイル: なし")
        self.file_path_label.pack(pady=5)
        
        # ボタンフレーム
        self.button_frame = ttk.Frame(self.transcribe_frame)
        self.button_frame.pack(pady=5)
        
        # 文字起こしボタン
        self.transcribe_button = ttk.Button(self.button_frame, 
                                          text="文字起こしを開始", 
                                          command=self.transcribe, 
                                          state=tk.DISABLED)
        self.transcribe_button.pack(side=tk.LEFT, padx=5)
        
        # テキストファイル保存ボタン
        self.save_button = ttk.Button(self.button_frame, 
                                    text="テキストファイルに保存", 
                                    command=self.save_to_file, 
                                    state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        # 結果表示用テキストボックス
        self.result_text = tk.Text(self.transcribe_frame, height=15, width=50)
        self.result_text.pack(pady=5)
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(self.transcribe_frame, 
                                orient=tk.VERTICAL, 
                                command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text['yscrollcommand'] = scrollbar.set

    def toggle_recording(self):
        if not self.recorder.recording:
            self.recorder.start_recording()
            self.record_button.config(text="録音停止", bg='#f44336')
            self.status_label.config(text="録音中...")
        else:
            self.current_audio_file = self.recorder.stop_recording()
            self.record_button.config(text="録音開始", bg='#4CAF50')
            self.status_label.config(text="録音完了")
            self.file_path_label.config(text=f"録音ファイル: {os.path.basename(self.current_audio_file)}")
            self.transcribe_button.config(state=tk.NORMAL)

    def select_file(self):
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
        if not self.current_audio_file:
            messagebox.showerror("エラー", "音声ファイルが選択されていません")
            return

        if not self.check_ffmpeg():
            messagebox.showerror("エラー", "FFmpegがインストールされていないか、PATHに追加されていません。")
            return

        try:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "文字起こしを開始しています...\n")
            self.root.update()

            if not self.model:
                self.model = whisper.load_model("medium")

            result = self.model.transcribe(self.current_audio_file)
            self.transcription_result = result["text"]
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, self.transcription_result)
            self.save_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("エラー", f"文字起こし中にエラーが発生しました: {str(e)}")

    def save_to_file(self):
        if not self.transcription_result:
            messagebox.showerror("エラー", "保存する文字起こし結果がありません")
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
                messagebox.showinfo("成功", "ファイルを保存しました")
            except Exception as e:
                messagebox.showerror("エラー", f"ファイルの保存中にエラーが発生しました: {str(e)}")

    def check_ffmpeg(self):
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except FileNotFoundError:
            return False

if __name__ == "__main__":
    root = tk.Tk()
    app = PyDiscussAssister(root)
    root.mainloop()

    


