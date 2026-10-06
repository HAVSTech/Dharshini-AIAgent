from __future__ import annotations
import queue
import threading
from dataclasses import dataclass
import numpy as np
import sounddevice as sd

INPUT_RATE=16000
OUTPUT_RATE=24000
CHANNELS=1
BLOCK_MS=100
INPUT_SAMPLES=INPUT_RATE*BLOCK_MS//1000

@dataclass
class AudioConfig:
    input_device:int|None=None
    output_device:int|None=None

class Microphone:
    def __init__(self, config:AudioConfig|None=None):
        self.config=config or AudioConfig()
        self.queue:queue.Queue[bytes]=queue.Queue(maxsize=32)
        self.stream=None
    def start(self):
        def callback(indata,frames,time_info,status):
            if status: print(f"[microphone] {status}")
            data=np.asarray(indata[:,0],dtype=np.int16).tobytes()
            try:self.queue.put_nowait(data)
            except queue.Full:pass
        self.stream=sd.InputStream(samplerate=INPUT_RATE,channels=1,dtype="int16",blocksize=INPUT_SAMPLES,device=self.config.input_device,callback=callback)
        self.stream.start()
    def read(self,timeout=1.0): return self.queue.get(timeout=timeout)
    def stop(self):
        if self.stream:self.stream.stop();self.stream.close();self.stream=None

class Speaker:
    def __init__(self,config:AudioConfig|None=None):
        self.config=config or AudioConfig()
        self.stream=None
        self.lock=threading.Lock()
    def start(self):
        self.stream=sd.OutputStream(samplerate=OUTPUT_RATE,channels=1,dtype="int16",device=self.config.output_device)
        self.stream.start()
    def play(self,data:bytes):
        if not data:return
        samples=np.frombuffer(data,dtype=np.int16)
        with self.lock:
            if self.stream:self.stream.write(samples.reshape(-1,1))
    def stop(self):
        if self.stream:self.stream.stop();self.stream.close();self.stream=None
