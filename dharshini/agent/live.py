from __future__ import annotations
import asyncio
from google import genai
from google.genai import types
from dharshini.audio import Microphone,Speaker,INPUT_RATE
from dharshini.config import Settings
from dharshini.memory import MemoryStore
from dharshini.safety import SafetyManager
from dharshini.tools.registry import TOOLS,declarations

class DharshiniAgent:
    def __init__(self,settings:Settings,memory:MemoryStore,safety:SafetyManager):
        self.settings=settings;self.memory=memory;self.safety=safety
        self.client=genai.Client(api_key=settings.api_key)

    async def text(self,prompt:str)->str:
        r=await self.client.aio.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=self.settings.system_prompt)
        )
        return r.text or ""

    async def voice(self)->None:
        mic=Microphone();speaker=Speaker();mic.start();speaker.start()
        try:
            cfg=types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                system_instruction=self.settings.system_prompt,
                input_audio_transcription=types.AudioTranscriptionConfig(),
                output_audio_transcription=types.AudioTranscriptionConfig(),
                tools=[types.Tool(function_declarations=declarations())],
            )
            async with self.client.aio.live.connect(model="gemini-3.8-live",config=cfg) as session:
                print(f"{self.settings.name} is listening. Ctrl+C to stop.")
                sender=asyncio.create_task(self._send_audio(session,mic))
                try:
                    async for response in session.receive():
                        if response.server_content:
                            c=response.server_content
                            if c.input_transcription: print(f"\nYou: {c.input_transcription.text}",flush=True)
                            if c.output_transcription: print(f"\n{self.settings.name}: {c.output_transcription.text}",flush=True)
                            if c.model_turn:
                                for part in c.model_turn.parts:
                                    if part.inline_data:speaker.play(part.inline_data.data)
                        if response.tool_call:
                            await self._handle_calls(session,response.tool_call.function_calls)
                finally: sender.cancel()
        finally:
            mic.stop();speaker.stop()

    async def _send_audio(self,session,mic):
        loop=asyncio.get_running_loop()
        while True:
            chunk=await loop.run_in_executor(None,mic.read)
            await session.send_realtime_input(audio=types.Blob(data=chunk,mime_type=f"audio/pcm;rate={INPUT_RATE}"))

    async def _handle_calls(self,session,calls):
        responses=[]
        for call in calls:
            spec=TOOLS.get(call.name)
            if not spec:
                responses.append(types.FunctionResponse(name=call.name,id=call.id,response={"error":"Unknown tool"}));continue
            if spec.risk!="SAFE":
                approval=self.safety.check(spec.risk,lambda:self._confirm(call.name,call.args))
                if not approval.allowed:
                    responses.append(types.FunctionResponse(name=call.name,id=call.id,response={"error":approval.reason}));continue
            try:
                result=spec.handler(**dict(call.args))
                self.memory.event("tool",f"{call.name}: {result}")
                responses.append(types.FunctionResponse(name=call.name,id=call.id,response={"result":result}))
            except Exception as exc:
                responses.append(types.FunctionResponse(name=call.name,id=call.id,response={"error":str(exc)}))
        await session.send_tool_response(function_responses=responses)

    def _confirm(self,name,args):
        print(f"\n[CONFIRM] {name} {dict(args)}")
        return input("Allow? [y/N]: ").strip().lower()=="y"
