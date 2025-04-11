import tkinter as tk
import pyaudio
import wave
import threading
import time
import os
from datetime import datetime


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

class RecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PyDiscussAssister")
        self.root.geometry("300x150")
        
        self.recorder = AudioRecorder()
        
        self.root.configure(bg='#f0f0f0')
        
        # ボタンの作成
        self.record_button = tk.Button(root, text="録音開始", 
                                     command=self.toggle_recording,
                                     bg='#4CAF50',
                                     fg='white',
                                     font=('Arial', 12),
                                     width=15,
                                     height=2)
        self.record_button.pack(pady=20)
        
        # ステータスラベル
        self.status_label = tk.Label(root, text="準備完了", 
                                   font=('Arial', 10),
                                   bg='#f0f0f0')
        self.status_label.pack(pady=10)

    def toggle_recording(self):
        if not self.recorder.recording:
            self.recorder.start_recording()
            self.record_button.config(text="録音停止", bg='#f44336')
            self.status_label.config(text="録音中...")
        else:
            self.recorder.stop_recording()
            self.record_button.config(text="録音開始", bg='#4CAF50')
            self.status_label.config(text="録音完了")

if __name__ == "__main__":
    root = tk.Tk()
    app = RecorderApp(root)
    root.mainloop()

    


