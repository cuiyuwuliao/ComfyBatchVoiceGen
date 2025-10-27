import os
import requests
import shutil
import json
import random
import sys
import re
import time
from pathlib import Path
import re
import codecs

currentDir = ""
currentPath = ""
rootDir = "\\\\share-office.xzoa.com\\NZ_AudioGroup_FullPackage"
if getattr(sys, 'frozen', False):
    currentDir = os.path.dirname(sys.executable)
    currentPath = os.path.abspath(sys.executable)
else:
    currentDir = os.path.dirname(os.path.abspath(__file__))
    currentPath = os.path.abspath(__file__)

# Replace any drive letter with the network root path
if len(currentDir) > 1 and currentDir[1] == ':':
    # Extract the path after the drive letter (e.g., "\Application\...")
    relative_path = currentDir[2:]
    currentDir = rootDir + relative_path

if len(currentPath) > 1 and currentPath[1] == ':':
    relative_path = currentPath[2:]
    currentPath = rootDir + relative_path

MODES = {1:"SimpleIndex2.json", 2:"SimpleVibeVoice.json", 3:"SimpleRVC.json"}
CURRENTMODE = 1
CURRENTTIME = str(int(time.time()))[::-1] #当前的epoch time倒过来, 用作生成文件夹的标识符
DGY = os.path.join(currentDir, "声音参考\\voice_DGY.wav")

def decode_unicode_escapes(text):
    return text
    try:
        decoded_text = codecs.decode(text, 'unicode_escape')
        return decoded_text
    except Exception as e:
        print(f"Error decoding text: {e}")
        return text
DGY = decode_unicode_escapes(DGY)
CURRENTVOICELINEFILE = ""
ALLOWEDRVCMODEL = [
    "local:LOL3.pth",
    "local:Monika.pth",
    "local:animus.pth",
    "local:goblin.pth",
    "local:goblinkuma.pth",
    "local:guanguanV1.pth",
    "local:keruanV1.pth",
    "local:kikiV1.pth",
    "local:monokuma_en.pth",
    "local:monokuma_jp.pth",
    "local:murloc_medium.pth",
    "local:nier_female.pth",
    "local:youzhanv2-xi.pth"
]

def clean_text(text_prompt:str):
    punctuation_map = {
        "，": ",",  # Chinese comma to English comma
        "。": ".",  # Chinese period to English period
        "！": "!",  # Chinese exclamation mark to English exclamation mark
        "？": "?",  # Chinese question mark to English question mark
        "“": "\"", # Chinese left quotation mark to English double quote
        "”": "\"", # Chinese right quotation mark to English double quote
        "‘": "'",  # Chinese left single quote to English single quote
        "’": "'",  # Chinese right single quote to English single quote
    }
    for chinese_punc, english_punc in punctuation_map.items():
        text_prompt = text_prompt.replace(chinese_punc, english_punc)
    cleaned = re.sub(r'[^\u4e00-\u9fffa-zA-Z0-9,.!?\"\']', '', text_prompt)
    return cleaned

def extract_valid_chars(s:str, num:int):
    valid_chars = []
    for char in s:
        if char.isdigit() or char.isalpha() or '\u4e00' <= char <= '\u9fff':
            valid_chars.append(char)
            if len(valid_chars) == num:
                break
    
    return ''.join(valid_chars)

def getset_cache_config(path, value = None):
    try:
        if value != None:
            with open(path, 'w', encoding='utf-8') as file:
                file.write(value)
        with open(path, 'r', encoding='utf-8') as file:
            value = file.read()
        return value
    except Exception as e:
        return None



# 首先需要把comfyUI->设置->服务器配置里: 输出路径改为"C:\\comfyTemp", 端口号改为7860
def generate_voice_comfyUI(prompt, outputPath, comfyUIConfig = None, cloneTarget = None, emotion = "耐心解释的语气"):
    if not prompt:
        print("! 没有台词, 跳过生成")
        return
    
    API_URL = getset_cache_config(os.path.join(currentDir, "API_URL.txt"))
    print(f"生成中: {prompt} - {API_URL}")
    if not cloneTarget:
        cloneTarget = DGY
    if CURRENTMODE == 1:#index2
        comfyUIConfig["6"]["inputs"]["value"] = prompt
        if cloneTarget:
            comfyUIConfig["3"]["inputs"]["audio"] = cloneTarget
        comfyUIConfig["7"]["inputs"]["emotion_text"] = emotion
        emotion, alpha = extract_float_after_separator(emotion)
        if alpha:
            comfyUIConfig["1"]["inputs"]["emotion_alpha"] = alpha
        
    elif CURRENTMODE == 2:#vibevoice
        comfyUIConfig["3"]["inputs"]["value"] = prompt
        if cloneTarget:
            comfyUIConfig["4"]["inputs"]["audio"] = cloneTarget
    elif CURRENTMODE == 3:#rvc
        if prompt:
            comfyUIConfig["4"]["inputs"]["audio"] = prompt #这个需要是一个原始音频的filepath
        prompt = os.path.basename(prompt).split(".")[0]#命名用
        
    outputAudioPath = os.path.join(outputPath, f"{CURRENTVOICELINEFILE}{str(CURRENTTIME)}")
    os.makedirs(outputAudioPath, exist_ok=True)
    outputAudioPath = os.path.join(outputAudioPath, f"{extract_valid_chars(prompt, 8)}.flac")

    response = requests.post(API_URL, json={"prompt" : comfyUIConfig})
    if response.status_code == 200:
        for _ in range (120):
            for filename in os.listdir(outputPath):
                if filename.startswith(str(CURRENTTIME)) and (".flac" in filename or ".wav" in filename):
                    shutil.move(os.path.join(outputPath, filename), outputAudioPath)
                    print(f"生成到了目录 -> 生成结果/{str(CURRENTTIME)}")
                    return outputAudioPath
            time.sleep(1)
        print(f"生成超时(检查GPU是否被占用): {outputAudioPath}")
        return outputAudioPath
    else:
        print(f"comfyUI语音生成失败: {response.status_code}, {response.text}")
        return None
    
def convert_linux_to_windows(linux_path):
    # Check if the path starts with '/mnt/<drive_letter>'
    if linux_path.startswith("/mnt/"):
        # Extract the drive letter
        drive_letter = linux_path[5].upper()  # Get the drive letter and make it uppercase
        # Replace '/mnt/<drive_letter>' with '<drive_letter>:'
        windows_path = linux_path.replace(f"/mnt/{linux_path[5]}", f"{drive_letter}:")
    else:
        # If it doesn't start with '/mnt/', just replace slashes
        windows_path = linux_path

    # Replace forward slashes with backslashes
    windows_path = windows_path.replace("/", "\\")
    return windows_path


def read_comfyUIConfig(path):
    with open(path, "r", encoding='utf-8') as file:
        data = json.load(file)
        dir = os.path.dirname(path)
        audio_path = os.path.join(dir, "声音参考")
        audio_path = os.path.join(audio_path, "voice_DGY.wav")
        rvc_path = os.path.join(dir, "变声模型")
        rvc_path = os.path.join(rvc_path, "guanguanV1.pth")
        if CURRENTMODE == 1:#index2
            data["3"]["inputs"]["audio"] = audio_path
            data["5"]["inputs"]["filename_prefix"] = str(CURRENTTIME)
            data["2"]["inputs"]["seed"] = random.randint(0, 2_147_483_647)
        elif CURRENTMODE == 2:#vibevoice
            data["4"]["inputs"]["audio"] = audio_path
            data["5"]["inputs"]["filename_prefix"] = str(CURRENTTIME)
            data["2"]["inputs"]["seed"] = random.randint(0, 2_147_483_647)
        elif CURRENTMODE == 3:#rvc
            data["1"]["inputs"]["model"] = rvc_path
            data["5"]["inputs"]["filename_prefix"] = str(CURRENTTIME)
    return data



def extract_float_after_separator(s):
    match = re.search(r'--(-?\d+\.?\d*)', s)
    if match:
        try:
            float_value = float(match.group(1))
            # Remove the "--float" part from the string
            string_without_flag = s[:match.start()] + s[match.end():]
            return (string_without_flag, float_value)
        except ValueError:
            return (s, None)
    return (s, None)

def validate_cloneTarget(path):
    if os.path.exists(path):
        return path
    folder = os.path.join(currentDir, "声音参考")
    for filename in os.listdir(folder):
        if filename.endswith(".wav") or filename.endswith(".flac") or filename.endswith(".mp3"):
            if path == filename or path == filename.split(".")[0]:
                return os.path.join(folder, filename)
    return ""

def read_voicelines(file_path):
    file_path = Path(file_path)
    if not file_path.exists():
        default_data = [
            {"voiceline": "我是一只快乐的小鸟", "emotion": "悲伤的语气", "speaker": "voice_DGY.wav"}
            for _ in range(10)
        ]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=2, ensure_ascii=False)
        return None
    
    # File exists, read and parse JSON
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    standardized_data = []
    for item in data:
        standardized_item = {
            "voiceline": item.get("voiceline", ""),
            "emotion": item.get("emotion", ""),
            "speaker": item.get("speaker", "")
        }
        standardized_data.append(standardized_item)
    return standardized_data

def get_audio_files():
    supported_formats = ('.wav', '.flac', '.mp3')
    while True:
        user_input = input("拖入要变声的音频文件或文件夹: ").strip()
        if not user_input:
            print("别留空")
            continue
        path = Path(user_input)
        if path.is_file():
            if path.suffix.lower() in supported_formats:
                print(f"找到音频文件: {path.name}")
                return [str(path)]
            else:
                print(f"格式不正确, 请使用音频文件: {', '.join(supported_formats)}")
                continue
        elif path.is_dir():
            audio_files = []
            for ext in supported_formats:
                audio_files.extend(path.glob(f"*{ext}"))
                audio_files.extend(path.glob(f"*{ext.upper()}"))
            
            if audio_files:
                audio_files = list(set(audio_files))  # Remove duplicates
                audio_files.sort()
                print(f"找到 {len(audio_files)}个音频文件:")
                for file in audio_files:
                    print(f"  - {file.name}")
                return [str(f) for f in audio_files]
            else:
                print(f"没有找到音频文件")
                continue
        else:
            print("路径不存在")
            continue

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            CURRENTMODE = int(sys.argv[1])
        except:
            CURRENTMODE = 1
    else:
        CURRENTMODE = 1
    print(f"*应用: {MODES[CURRENTMODE]}")

    configFile = os.path.join(currentDir, MODES[CURRENTMODE])
    configData = read_comfyUIConfig(configFile)
    outputPath = os.path.join(currentDir, "生成结果")

    if CURRENTMODE in [3, "3"]:
        files = get_audio_files()
        pthFile = ""
        print("\n当前可用声线模型: ")
        while True:
            index = 1
            for m in ALLOWEDRVCMODEL:
                print(f"{index}: {m}", flush= True)
                index += 1
            user_input = input("输入要使用声线的序号: ")
            try:
                pthFile = ALLOWEDRVCMODEL[int(user_input)-1]
                print(f"使用声线: {pthFile}")
                break
            except:
                continue
        os.system('cls')
        for file in files:
            generate_voice_comfyUI(decode_unicode_escapes(file), decode_unicode_escapes(outputPath) ,configData, cloneTarget = decode_unicode_escapes(pthFile))
            print("-------------------------------------")
        input("生成结束, 按回车退出")
        sys.exit()



    voicelinePath = os.path.join(currentDir, "台本")
    voicelineExample = os.path.join(voicelinePath, "示例.json")
    if not os.path.exists(voicelineExample):
        read_voicelines(voicelineExample)

    voicelineDict = {}
    index = 1
    for filename in os.listdir(voicelinePath):
        if filename.endswith(".json"):
            if filename == "示例.json":
                continue
            voicelineDict[index] = filename
            index += 1
    if voicelineDict == {}:
        print("你还没有台本, 请在台本文件夹内按照示例.json的格式创建台本")
    else:
        print("读取到以下台本: ")

    for index, voicelineFile in voicelineDict.items():
        print(f"{index}: {voicelineFile}")

    user_input = ""
    while not user_input:
        user_input = input("输入台本序号(或要生成的文字): ")
    os.system('cls')
    try:
        voicelines = read_voicelines(os.path.join(voicelinePath, voicelineDict.get(int(user_input))))
        if not voicelines:
            raise RuntimeError
        CURRENTVOICELINEFILE = voicelineDict.get(int(user_input)).replace(".json", "")
        print(f"即将生成以下内容:\n{json.dumps(voicelines, indent=2, ensure_ascii=False)}")
    except:
        print(f"(未成功读取台本)即将生成以下内容:\n{user_input}")
        user_input_clone = ""
        while not os.path.exists(user_input_clone):
            user_input_clone = input("\n\n拖入一个参考语音文件(你也可以输入\"skip\"来使用默认的声音):")
            if user_input_clone.lower() == "skip":
                user_input_clone = DGY
                break
        voicelines = [{"voiceline":user_input, "speaker":user_input_clone, "emotion":"激昂的语气"}]

    print("\n")
    for line in voicelines:
        cloneTargetPath = line.get("speaker")
        cloneTargetPath = validate_cloneTarget(cloneTargetPath)
        prompt = line.get("voiceline")
        if not prompt:
            print("! voiceline为空的台词将跳过生成")
        elif not cloneTargetPath:
            print(f"! 克隆声音不存在: {line.get("speaker")}")

    input("\n确认无误后, 按回车开始生成")
    os.system('cls')
    for line in voicelines:
        cloneTargetPath = line.get("speaker")
        cloneTargetPath = validate_cloneTarget(cloneTargetPath)
        prompt = line.get("voiceline")
        if not prompt:
            print(f"! voiceline为空, 跳过生成")
            continue
        if not cloneTargetPath:
            print(f"! 克隆的声音不存在: {line.get("speaker")}, 使用默认声音")
            cloneTargetPath = DGY
        emotionDescription = line.get("emotion")

        generate_voice_comfyUI(decode_unicode_escapes(prompt), decode_unicode_escapes(outputPath) ,configData, cloneTarget = decode_unicode_escapes(cloneTargetPath), emotion = decode_unicode_escapes(emotionDescription))
        print("-------------------------------------")
    input("生成结束, 按回车退出")
    sys.exit()

    