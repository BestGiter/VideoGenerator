import pygame, pyttsx3, os, glob
import requests, random, shutil, subprocess
    
RECORD = True
    
pygame.init()
screen = pygame.display.set_mode((400, 400))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 50)
pygame.mixer.init()
engine = pyttsx3.init()
text = """
<excited>
[Welcome to today's coding video, (HELLO WORLD):VIDEO 1, (HELLO WORLD!)]
<happy>
[You might be wondering:????][How do you code:coding??]
[Well the first thing you'll probably do is a Hello World Program:Hello World Program]
[To write a hello world program in python, write print Hello World!:print("Hello World!")]
<excited>
[Goodbye, and thanks for watching!:THANKS FOR WATCHING!!]
"""
def without_tags(text):
    res = ""
    repeat = True
    for x in text:
        if x not in "[:]<>" and repeat:
            res += x
        if x == ":":
            repeat = False
        if x == "]":
            repeat = True
    return res
def segments_gen(text):
    # fine ill make a lexer
    segments = []
    segment = ""
    for i,x in enumerate(text):
        if x == "[":
            if segment: segments.append(segment)
            segment = "["
        elif x == "]":
            if segment: segments.append(segment+"]")
            segment = ""
        elif x == "<":
            if segment: segments.append(segment)
            segment = "<"
        elif x == ">":
            if segment: segments.append(segment+">")
            segment = ""
        else:
            segment += x
    if segment: segments.append(segment)
    return segments
images = {}
faces = {}
def getface(name):
    if name not in faces:
        images[name] = pygame.image.load(name+".png")
    return images[name]
def getimage(name):
    if name not in images:
        surf = pygame.Surface((400, 400))
        col = (random.randint(0, 255),random.randint(0, 255),random.randint(0, 255))
        av = (col[0]+col[1]+col[2])/3
        surf.fill(col)
        text = font.render(name, False, (255, 255, 255) if av < 128 else (0, 0, 0))
        aspect = text.get_height()/text.get_width() if text.get_width() > 0 else 0
        nheight = aspect*200
        scaled = pygame.transform.scale(text, (200,nheight))
        surf.blit(scaled, scaled.get_rect(center=(200, 200)))
        pygame.draw.rect(surf, (255-col[0], 255-col[1], 255-col[2]), (0, 250, 150, 150))
        images[name] = surf
    return images[name]  
            

if not os.path.exists("temp_voices"):
    os.mkdir("temp_voices")
    
if not os.path.exists("temp_images"):
    os.mkdir("temp_images")
if RECORD:
    if os.path.exists("temp_frames"):
        shutil.rmtree("temp_frames")
    if not os.path.exists("temp_frames"):
        os.mkdir("temp_frames")
lines = text.split("\n")
segments = []
for l in lines:
    segments.extend(segments_gen(l))
print(segments)
segments_t = [without_tags(t) for t in segments]
print(segments_t)
i = 0
for s in segments:
    if s[0] == "[":
        getimage(s[1:-1].split(":")[1] if ":" in s else segments_t[i])
    elif s[0] == "<":
        getface(segments_t[i])
    i += 1
i = 0
for l in segments_t:
    if l and segments[i][0] != "<": engine.save_to_file(l, f"temp_voices/voice_{i}.wav")
    i += 1
engine.runAndWait()
i = 0
t = 0
sounds = {}
image = ""
def sound(name):
    if name not in sounds: sounds[name] = pygame.mixer.Sound(name)
    return sounds[name]

pygame.mixer.music.load("elevatormusic.mp3")
pygame.mixer.music.play(-1)
pygame.mixer.music.set_volume(0.3)
frame = 0
frame_changed = False
durations = []
last = 0
first = True
while True:
    dt = clock.tick(60)/1000 if not RECORD else 1/60
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
    if i < len(segments_t):
        if segments_t[i]:
            if t == 0:
                if segments[i][0] == "[":
                    image = segments[i][1:-1].split(":")[1] if ":" in segments[i] else segments_t[i]
                    frame_changed = True
                elif segments[i][0] == "<":
                    face = segments_t[i]
                    frame_changed = True
            if segments[i][0] != "<":
                s = sound(f"temp_voices/voice_{i}.wav")
                l = s.get_length()
                if t == 0:
                    s.play()
                t += dt
                if t >= l:
                    i += 1
                    t = 0
            else:
                i += 1
                t = 0
    else:
        pygame.quit()
        break
    screen.fill((0, 0, 0))
    if g := getimage(image):
        screen.blit(g, (0, 0))
    if f := getface(face):
        screen.blit(pygame.transform.scale(f, (150, 150)), (0, 250))
    if RECORD and frame_changed:
        if not first:
            durations.append((last[0], (frame-last[1])/60))
        last = (f"temp_frames/frame_{frame:06d}.png", frame)
        pygame.image.save(screen, f"temp_frames/frame_{frame:06d}.png")
        frame_changed = False
    pygame.display.flip()
    frame += 1
    first = False
durations.append((last[0], (frame-last[1])/60))
if RECORD:
    with open("audio.txt", "w") as f:
        for i in range(len(segments_t)):
            if segments_t[i] and segments[i][0] != "<": f.write(f"file 'temp_voices/voice_{i}.wav'\n")
    with open("frames.txt", "w") as f:
        for name, dur in durations:
            f.write(f"file '{name}'\nduration {dur}\n")
    r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "audio.txt", "-c", "copy", "voices_combined.wav"],    capture_output=True,text=True)
    print(r.stderr)
    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", "elevatormusic.mp3",
        "-i", "voices_combined.wav",
        "-filter_complex", "[0:a]volume=0.3[aquiet];[aquiet][1:a]amix=inputs=2:duration=shortest",
        "-shortest",
        "mixed_audio.wav"
    ], capture_output=True, text=True)
    print(r.stderr)
    r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "frames.txt", "-i", "mixed_audio.wav", "-pix_fmt", "yuv420p", "output.mp4"],    capture_output=True,text=True)
    print(r.stderr)