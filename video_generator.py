import pygame, pyttsx3, os, glob
import requests, random, shutil, subprocess

"""

WARNING: ONLY WORKS ON WINDOWS

=== INSTRUCTIONS ===
To use:
1. delete temp_voices and temp_frames folder
2. edit the text variable
3. press run
4. rename output.mp4

"""

RECORD = True
    
pygame.init()
screen = pygame.display.set_mode((400, 400))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 50)
pygame.mixer.init()
engine = pyttsx3.init()

text = """
<excited><happy><sad>
[said:shown]
[said:{square(randcol, center, 200;200, "shown")}]
[said:{image("excited.png",stretch)}]
"""
def without_tags(text):
    res = ""
    repeat = True
    i = 0
    while i < len(text):
        x = text[i]
        if x not in "[:]<>|\\" and repeat:
            res += x
        if x == ":":
            repeat = False
        if x == "]":
            repeat = True
        if x == "|":
            repeat = not repeat
        if x == "\\" and repeat:
            if i+1 < len(text):
                if text[i+1] == "n":
                    res += "\n"
                else:
                    res += text[i+1]
                i += 1
        i += 1
        
    return res
def shown(text):
    res = ""
    repeat = False
    i = 0
    while i < len(text):
        x = text[i]
        if x not in "[:]<>|\\" and repeat:
            res += x
        if x == ":":
            repeat = True
        if x == "]":
            repeat = False
        if x == "|":
            repeat = not repeat
        if x == "\\":
            if i+1 < len(text):
                if text[i+1] == "n":
                    res += "\n"
                else:
                    res += text[i+1]
                i += 1
        i += 1
        
    return res
def segments_gen(text):
    # fine ill make a lexer
    segments = []
    segment = ""
    lined = False
    i = 0
    while i < len(text):
        x = text[i]
        did = False
        if x == "[":
            did = True
            if segment: segments.append(segment)
            segment = "["
        elif x == "]":
            did = True
            if segment: segments.append(segment+"]")
            segment = ""
        elif x == "<":
            did = True
            if segment: segments.append(segment)
            segment = "<"
        elif x == ">":
            did = True
            if segment: segments.append(segment+">")
            segment = ""
        elif x == "|" and not lined:
            did = True
            lined = True
            if segment: segments.append(segment)
            segment = "|"
        elif x == "|" and lined:
            did = True
            lined = False
            if segment: segments.append(segment+"|")
            segment = ""
        elif x == "\\":
            did = True
            if i+1 < len(text):
                if text[i+1] == "n":
                    segment += "\n"
                else:
                    segment += text[i+1]
                i += 1
        if not did: segment += x
        i += 1
            
    if segment: segments.append(segment)
    return segments
def seconds_to_srt(t):
    hours = int(t // 3600)
    minutes = int((t % 3600) // 60)
    seconds = int(t % 60)
    millis = int((t - int(t)) * 1000)

    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"
images = {}
faces = {}
def getface(name):
    if name not in faces:
        images[name] = pygame.image.load(name+".png")
    return images[name]
def parse_command(command):
    i = 0
    def peek():
        return command[i]
    def eat():
        nonlocal i
        i += 1
        return command[i-1]
    def skip_spaces():
        while peek() == " ":
            eat()
    def is_name(name):
        nonlocal i
        ni = i
        for n in name:
            if peek() == n:
                eat()
            else:
                i = ni
                return False
        return True
    def parse_graphic_name():
        names = ["square", "image"]
        for n in names:
            if is_name(n):
                return n
    def parse_keyword():
        keywords = ["stretch", "width", "height"]
        for k in keywords:
            if is_name(k):
                return k
        return None
    def parse_number():
        num = 0
        ran = False
        while peek() in "0123456789":
            ran = True
            num *= 10
            num += int(eat())
        return num if ran else None
    def parse_color():
        nonlocal i
        ni = i
        if is_name("randcol"):
            return (random.randint(0, 255),random.randint(0, 255),random.randint(0, 255))
        if peek() != "#":
            return None
        eat()
        rgb = []
        for _ in range(3):
            rgb.append(0)
            for j in range(2):
                if peek() in "0123456789ABCDEFabcdef":
                    rgb[-1] *= 16
                    rgb[-1] += int(eat(), 16)
                else:
                    i = ni
                    return None
        return tuple(rgb)
    def parse_pair():
        nonlocal i
        if is_name("center"):
            return "center"
        ni = i
        num1 = parse_number()
        if num1 is None:
            i = ni
            return None
        if peek() != ";":
            i = ni
            return None
        eat()
        num2 = parse_number()
        if num2 is None:
            i = ni
            return None
        return (num1, num2)
    def parse_string():
        nonlocal i
        string = ""
        if peek() == "\"":
            eat()
            while peek() != "\"":
                string += eat()
            eat()
            return string
        else:
            return None
    def parse_param():
        res = parse_pair()
        if res is not None:
            return res
        res = parse_number()
        if res is not None:
            return res
        res = parse_color()
        if res is not None:
            return res
        res = parse_string()
        if res is not None:
            return res
        res = parse_keyword()
        if res is not None:
            return res
        return None
    def parse_graphic():
        res = parse_graphic_name()
        if res is not None:
            if peek() == "(":
                eat()
                params = []
                while peek() != ")":
                    params.append(parse_param())
                    if params[-1] is None:
                        return (res, *params[:-1])
                    if peek() != ",":
                        return (res, *params)
                    eat()
                    skip_spaces()
                eat()
                return (res, *params[:-1])
        return None
    return parse_graphic()
def getimage(name):
    if name not in images:
        surf = pygame.Surface((400, 400))
        col = (random.randint(0, 255),random.randint(0, 255),random.randint(0, 255))
        av = (col[0]+col[1]+col[2])/3
        surf.fill(col)
        if not name or name[0] != "{":
            text = font.render(name, False, (255, 255, 255) if av < 128 else (0, 0, 0))
            aspect = text.get_height()/text.get_width() if text.get_width() > 0 else 0
            nheight = aspect*200
            scaled = pygame.transform.scale(text, (200,nheight))
            surf.blit(scaled, scaled.get_rect(center=(200, 200)))
        else:
            command = name[1:-1]
            print(command)
            parsed = parse_command(command)
            print(parsed)
            if parsed[0] == "square":
                pos = parsed[2]
                if pos == "center":
                    pos = (200-parsed[3][0]/2, 200-parsed[3][1]/2)
                pygame.draw.rect(surf, parsed[1], [*pos, *parsed[3]])
                pygame.draw.rect(surf, (0, 0, 0), [*pos, *parsed[3]], width=2)
                av = (parsed[1][0]+parsed[1][1]+parsed[1][2])/3
                text = font.render(parsed[4], False, (255, 255, 255) if av < 128 else (0, 0, 0))
                aspect = text.get_height()/text.get_width() if text.get_width() > 0 else 0
                nheight = aspect*parsed[3][0]/2
                scaled = pygame.transform.scale(text, (parsed[3][0]/2,nheight))
                surf.blit(scaled, scaled.get_rect(center=(pos[0]+parsed[3][0]/2, pos[1]+parsed[3][0]/2)))
            elif parsed[0] == "image":
                path = parsed[1]
                mode = parsed[2] if len(parsed) >= 3 else "stretch"

                img = pygame.image.load(path)
                w, h = img.get_size()
                if mode == "stretch":
                    img = pygame.transform.scale(img, (400, 400))

                elif mode == "width":
                    nh = int(h * (400 / w))
                    img = pygame.transform.scale(img, (400, nh))

                elif mode == "height":
                    nw = int(w * (400 / h))
                    img = pygame.transform.scale(img, (nw, 400))
                surf.blit(img, img.get_rect(center=(200, 200)))
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
        getimage(shown(s) if ":" in s else segments_t[i])
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
transition = "none"
lastimage = ""
image = ""
transtime = 0
face = "happy"
captionstamps = []
while True:
    dt = clock.tick(60)/1000 if not RECORD else 1/60
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
    if i < len(segments_t):
        if t == 0:
            captionstamps.append(frame/60)
        if segments_t[i]:
            if t == 0:
                if segments[i][0] == "[":
                    lastimage = image
                    image = shown(segments[i]) if ":" in segments[i] else segments_t[i]
                    frame_changed = True
                elif segments[i][0] == "<":
                    face = segments_t[i]
                    frame_changed = True
            if segments[i][0] not in "<|":
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
            if segments[i][0] == "|":
                transition = segments[i][1:-1]
                transtime = 0
            i += 1
            t = 0
    else:
        pygame.quit()
        break
    screen.fill((0, 0, 0))
    if (g := getimage(image)) and (h := getimage(lastimage)):
        if transition == "none":
            screen.blit(g)
        elif transition == "slide":
            screen.blit(g, (400-transtime*400, 0))
            screen.blit(h, (-transtime*400, 0))
    if f := getface(face):
        screen.blit(pygame.transform.scale(f, (150, 150)), (0, 250))
    if transition != "none":
        transtime += dt
        frame_changed = True
        if transtime >= 1:
            transtime = 0
            transition = "none"
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
            if os.path.exists(f"temp_voices/voice_{i}.wav"): f.write(f"file 'temp_voices/voice_{i}.wav'\n")
    with open("frames.txt", "w") as f:
        for name, dur in durations:
            f.write(f"file '{name}'\nduration {dur}\n")
    with open("captions.srt", "w") as f:
        for i, c in enumerate(captionstamps):
            next_ = captionstamps[i+1] if i+1 < len(captionstamps) else frame/60
            caption = segments_t[i]
            f.write(f"{i+1}\n{seconds_to_srt(c)} --> {seconds_to_srt(next_)}\n{caption}\n\n")
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
    r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "frames.txt", "-i", "mixed_audio.wav", "-i", "captions.srt", "-pix_fmt", "yuv420p", "-c:s", "mov_text", "output.mp4"],    capture_output=True,text=True)
    print(r.stderr)
