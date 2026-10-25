#!/usr/bin/env python3
"""Forge short renderer. Publish only after final-file audio/video QA and manual playback review."""
import argparse, json, math, os, re, subprocess, tempfile, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W,H,FPS,SR=720,1280,20,32000
LINES=[
 'その仕事、AIに丸投げして大丈夫？',
 '判断が必要。毎回手順が違う。ミスの影響が大きい。',
 'この三つは、人の確認を残そう。',
 '最初に任せるなら、繰り返しで、手順が決まっていて、結果を確かめやすい仕事。',
 'AI導入は、小さく始めよう。',
]
FONT_CANDIDATES=[
 '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
 '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
 '/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc',
 '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
]
def run(cmd):
 subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
def validate_output(path):
 # A successfully exited ffmpeg process is not proof that the final MP4 has audible audio.
 probe=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_type','-of','json',str(path)],capture_output=True,text=True,check=True)
 types={s.get('codec_type') for s in json.loads(probe.stdout).get('streams',[])}
 if not {'video','audio'}.issubset(types):
  raise RuntimeError('Export QA failed: video or audio stream missing')
 decoded=subprocess.run(['ffmpeg','-hide_banner','-nostdin','-i',str(path),'-vn','-af','volumedetect','-f','null','-'],capture_output=True,text=True)
 if decoded.returncode:
  raise RuntimeError('Export QA failed: audio decode error')
 peak=re.search(r'max_volume:\\s*(-?[0-9.]+) dB',decoded.stderr)
 if not peak or float(peak.group(1)) < -48:
  raise RuntimeError('Export QA failed: audio is silent or too quiet')
 # This verifies audio presence, not speech clarity, caption timing, or mix balance.
 # Listen to and inspect the actual final MP4 before any public scheduling.

def font(size,bold=False):
 paths=FONT_CANDIDATES if bold else FONT_CANDIDATES[1:2]+FONT_CANDIDATES[:1]+FONT_CANDIDATES[2:]
 for path in paths:
  if os.path.exists(path):return ImageFont.truetype(path,size,index=0)
 raise RuntimeError('Japanese font not installed')
def make_voice(work,mock):
 chunks=[];spans=[];pos=0
 for i,line in enumerate(LINES):
  if mock:
   duration=[3.1,5.6,3.4,8.1,2.9][i]
   arr=np.zeros(round(SR*duration),dtype=np.float32)
  else:
   from gtts import gTTS
   mp3=work/f'part{i}.mp3';raw=work/f'part{i}.wav'
   gTTS(line,lang='ja',slow=False).save(str(mp3))
   run(['ffmpeg','-y','-i',str(mp3),'-ar',str(SR),'-ac','1',str(raw)])
   with wave.open(str(raw),'rb') as f:
    arr=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float32)/32768
   if np.sqrt(np.mean(arr**2))<.008:raise RuntimeError('TTS audio failed quality check: silent')
  start=pos/SR;chunks.append(arr);pos+=len(arr);spans.append((start,pos/SR))
  pause=np.zeros(round(.17*SR),dtype=np.float32);chunks.append(pause);pos+=len(pause)
 return np.concatenate(chunks),spans
def synth_music(n,spans):
 music=np.zeros(n,dtype=np.float32);beat=60/112;notes=[130.81,155.56,196.0,233.08]
 for j,at in enumerate(np.arange(0,n/SR,beat/2)):
  start=int(at*SR);length=min(int(.38*SR),n-start)
  if length<=0:break
  z=np.arange(length,dtype=np.float32)/SR;freq=notes[(j//2)%len(notes)]*(2 if j%4==0 else 1)
  env=(1-np.exp(-z*90))*np.exp(-z*8)
  music[start:start+length]+=.045*env*(np.sin(2*np.pi*freq*z)+.25*np.sin(2*np.pi*freq*2*z))
 for at in np.arange(0,n/SR,beat):
  start=int(at*SR);length=min(int(.16*SR),n-start)
  if length<=0:break
  z=np.arange(length,dtype=np.float32)/SR;env=np.exp(-z*30)
  music[start:start+length]+=.065*env*np.sin(2*np.pi*(55+70*np.exp(-z*35))*z)
 rng=np.random.default_rng(42)
 for a,b in spans[1:]:
  start=max(0,int((a-.22)*SR));length=min(int(.43*SR),n-start)
  if length<=0:continue
  z=np.linspace(0,1,length,dtype=np.float32)
  noise=np.convolve(rng.standard_normal(length).astype(np.float32),np.ones(70)/70,mode='same')
  music[start:start+length]+=.025*np.sin(np.pi*z)*noise
 return music
def audio_file(path,voice,spans,dur):
 n=round(dur*SR);music=synth_music(n,spans);v=np.zeros(n,dtype=np.float32)
 offset=int(.18*SR);end=min(n,offset+len(voice));v[offset:end]=voice[:end-offset]
 pcm=np.round(np.clip(.84*v+music,-.96,.96)*32767).astype('<i2')
 stereo=np.stack([pcm,pcm],axis=-1)
 with wave.open(str(path),'wb') as f:
  f.setnchannels(2);f.setsampwidth(2);f.setframerate(SR);f.writeframes(stereo.tobytes())
def rounded(d,xy,fill,r=20,outline=None,width=1):
 d.rounded_rectangle(tuple(map(int,xy)),radius=r,fill=fill,outline=outline,width=width)
def text(d,xy,s,size,fill='#FFFFFF',bold=False,anchor=None,spacing=6):
 d.multiline_text(xy,s,font=font(size,bold),fill=fill,anchor=anchor,spacing=spacing,align='center' if anchor and 'm' in anchor else 'left')
def ease(x):
 x=max(0,min(1,x));return 1-(1-x)**3
def base_bg():
 y=np.linspace(0,1,H,dtype=np.float32)[:,None,None]
 x=np.linspace(0,1,W,dtype=np.float32)[None,:,None]
 top=np.array([12,16,24],dtype=np.float32).reshape(1,1,3)
 bot=np.array([25,30,41],dtype=np.float32).reshape(1,1,3)
 rgb=np.broadcast_to(top*(1-y)+bot*y,(H,W,3)).copy()
 glow=np.exp(-(((x-.83)/.48)**2+((y-.15)/.27)**2)*2)
 rgb+=glow*np.array([24,11,2],dtype=np.float32).reshape(1,1,3)
 return Image.fromarray(np.uint8(np.clip(rgb,0,255)),'RGB')
BG=base_bg()
def card(d,y,num,label,sub,accent,progress):
 shift=round(75*(1-ease(progress)))
 rounded(d,(60+shift,y,660+shift,y+135),(34,40,51),20,outline=(62,70,81),width=2)
 rounded(d,(60+shift,y,69+shift,y+135),accent,4)
 text(d,(95+shift,y+26),num,25,accent,bold=True)
 text(d,(166+shift,y+18),label,43,(247,247,247),bold=True)
 text(d,(166+shift,y+83),sub,22,(177,187,200))
def render_frame(t,spans,dur,mock=False):
 im=BG.copy();d=ImageDraw.Draw(im)
 for xx in range(36,W,90):d.line((xx,80,xx,H-90),fill=(28,33,44),width=1)
 for yy in range(140,H,90):d.line((34,yy,W-34,yy),fill=(28,33,44),width=1)
 d.ellipse((W-220,-125,W+110,205),outline=(63,45,33),width=2)
 d.ellipse((W-170,-75,W+60,155),outline=(93,59,37),width=2)
 text(d,(56,64),'F O R G E',30,(246,246,247),bold=True)
 rounded(d,(540,70,662,105),(50,38,28),12)
 text(d,(559,77),'AI 仕事術',19,(244,157,85),bold=True)
 d.line((54,117,666,117),fill=(63,66,73),width=2)
 text(d,(58,1175),'AI OPERATIONS STUDIO',20,(135,145,160),bold=True)
 d.line((58,1154,662,1154),fill=(63,66,73),width=2)
 s=[0]+[v[1]+.17 for v in spans]
 if t<s[1]:
  text(d,(62,250),'その仕事、',65,(235,238,243),bold=True)
  text(d,(62,360),'AIに丸投げ？',80,(247,149,70),bold=True)
  text(d,(64,490),'まずは立ち止まって考えよう。',30,(195,202,210))
  cx,cy=360,760;radius=150+8*math.sin(t*2)
  d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),outline=(246,145,73),width=5)
  text(d,(cx,cy),'!',180,(255,174,102),bold=True,anchor='mm')
 elif t<s[2]:
  text(d,(58,210),'AIに丸投げする前に',50,(243,245,248),bold=True)
  text(d,(60,285),'注意したい3つ',58,(248,149,70),bold=True)
  p=(t-s[1])/(s[2]-s[1])
  for i,(label,sub) in enumerate([('判断が必要','人が考える部分が多い'),('手順が毎回違う','例外が多く、ルールが曖昧'),('ミスの影響が大きい','確認なしでは危険')]):
   card(d,435+i*162,f'0{i+1}',label,sub,(244,146,73),p*3-i*.65)
 elif t<s[3]:
  text(d,(58,290),'だからこそ',53,(235,238,242),bold=True)
  text(d,(58,395),'人の確認は',73,(248,151,75),bold=True)
  text(d,(58,495),'残しておく。',73,(248,151,75),bold=True)
  rounded(d,(75,740,645,860),(32,41,51),26,outline=(73,88,93),width=2)
  text(d,(160,775),'AI  ＋  HUMAN',42,(219,227,231),bold=True)
 elif t<s[4]:
  text(d,(58,225),'最初に任せるなら',51,(237,241,244),bold=True)
  text(d,(58,298),'この3条件から。',56,(248,151,75),bold=True)
  p=(t-s[3])/(s[4]-s[3])
  for i,(label,sub) in enumerate([('繰り返す','毎週・毎日発生する'),('手順が決まる','ルールを書き出せる'),('確認しやすい','結果を人が検証できる')]):
   card(d,448+i*162,f'0{i+1}',label,sub,(130,208,185),p*3-i*.65)
 else:
  text(d,(58,335),'AI導入は、',65,(239,240,242),bold=True)
  text(d,(58,448),'小さく始めよう。',72,(247,149,70),bold=True)
  rounded(d,(58,690,662,817),(36,43,52),22,outline=(98,72,52),width=2)
  text(d,(90,725),'まずは1つの仕事から',43,(238,240,242),bold=True)
  text(d,(58,990),'FORGE',78,(248,248,250),bold=True)
 seg=0
 for i,(a,b) in enumerate(spans):
  if t>=a+.18:seg=i
 if t<=spans[-1][1]+.18:
  line=LINES[seg]
  if seg==1:line='判断が必要。毎回手順が違う。\nミスの影響が大きい。'
  if seg==3:line='最初に任せるなら、繰り返しで、\n手順が決まっていて、\n結果を確かめやすい仕事。'
  if len(line)>28 and '\n' not in line:line=line[:17]+'\n'+line[17:]
  rounded(d,(42,990,678,1135),(10,13,19),18,outline=(75,78,84),width=1)
  text(d,(360,1060),line,29 if seg==3 else 34,(249,250,252),bold=True,anchor='mm',spacing=8)
 d.rectangle((58,123,58+int(604*min(1,t/dur)),128),fill=(244,146,73))
 if mock:
  rounded(d,(40,133,680,198),(110,30,30),12)
  text(d,(60,149),'仮音声プレビュー・公開不可',28,(255,255,255),bold=True)
 return im
def main():
 p=argparse.ArgumentParser();p.add_argument('--mock-voice',action='store_true');p.add_argument('--output',default='assets/shorts/forge-ai-review-20261012.mp4');a=p.parse_args()
 if a.mock_voice and not any(tag in Path(a.output).stem.lower() for tag in ('preview','mock')):
  p.error('--mock-voice is preview-only: output filename must contain preview or mock')
 Path(a.output).parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory() as td:
  work=Path(td);voice,spans=make_voice(work,a.mock_voice);dur=max(23.8,spans[-1][1]+1.4)
  audio_file(work/'mix.wav',voice,spans,dur)
  cmd=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-vcodec','rawvideo','-s',f'{W}x{H}','-pix_fmt','rgb24','-r',str(FPS),'-i','-','-c:v','libx264','-preset','veryfast','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',str(work/'silent.mp4')]
  proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
  for k in range(math.ceil(dur*FPS)):proc.stdin.write(render_frame(k/FPS,spans,dur,a.mock_voice).tobytes())
  proc.stdin.close();rc=proc.wait()
  if rc:raise RuntimeError('ffmpeg failed: '+str(rc))
  # Stage beside the destination so a rejected export can never overwrite the last good file.
  fd,staged_name=tempfile.mkstemp(prefix='.forge-qa-',suffix='.mp4',dir=str(Path(a.output).parent))
  os.close(fd);staged=Path(staged_name)
  try:
   run(['ffmpeg','-y','-loglevel','error','-i',str(work/'silent.mp4'),'-i',str(work/'mix.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','160k','-shortest','-movflags','+faststart',str(staged)])
   validate_output(staged)
   os.replace(staged,a.output)
  finally:
   staged.unlink(missing_ok=True)
  print({'output':a.output,'duration':round(dur,2),'spans':spans,'bytes':Path(a.output).stat().st_size,'qa':'audio+video streams, non-silent decoded audio; manual review still required'})
if __name__=='__main__':main()
