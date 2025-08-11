import subprocess
import random
import os
from pathlib import Path
from config import PHOTO_DIR, VIDEO_DIR

def choose_file(option: str, quantity: int) -> list[str]:
    if option == 'photos':
        chosen_dir = PHOTO_DIR
        extensions = ('.png', '.jpg', '.jpeg')
    elif option == 'videos':
        chosen_dir = VIDEO_DIR
        extensions = ('.mp4', '.mov', '.avi', '.mkv')
    else:
        raise ValueError("option must be 'photos' or 'videos'")

    # Получаем все файлы с нужным расширением
    files = [
        os.path.join(chosen_dir, f)
        for f in os.listdir(chosen_dir)
        if os.path.isfile(os.path.join(chosen_dir, f)) and f.lower().endswith(extensions)
    ]

    if not files:
        raise FileNotFoundError(f"No media files found in {chosen_dir} with extensions {extensions}")

    # Случайный выбор без повторений
    return random.sample(files, min(quantity, len(files)))

def unique_media(input_path: str, output_path: str) -> str:
    input_path = Path(input_path.strip())
    output_path = Path(output_path.strip())

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # 📸 Базовые рандомные параметры
    brightness = round(random.uniform(-0.05, 0.05), 3)
    contrast = round(random.uniform(0.9, 1.2), 2)
    noise = random.randint(5, 30)
    hue_shift = random.randint(-10, 10)
    hue_saturation = round(random.uniform(0.9, 1.1), 2)
    crop_enabled = random.random() > 0.7
    sharpen_enabled = random.random() > 0.5
    blur_enabled = not sharpen_enabled and random.random() > 0.5
    flip_enabled = random.choice([True, False])
    rotate_angle = random.choice([0, 0.01, -0.01, 0.02, -0.02])  # в радианах
    fps_change = random.choice([None, 29.97, 31.0, 27.0])

    # 🧪 Собираем фильтры
    filters = [
        f"eq=brightness={brightness}:contrast={contrast}",
        f"noise=alls={noise}:allf=t",
        f"hue=h={hue_shift}:s={hue_saturation}",
        f"rotate={rotate_angle}:ow=rotw({rotate_angle}):oh=roth({rotate_angle})" if rotate_angle else "",
        "hflip" if flip_enabled else "",
        "crop=in_w*0.97:in_h*0.97" if crop_enabled else "",
        "unsharp=5:5:1.0" if sharpen_enabled else "",
        "gblur=sigma=0.3" if blur_enabled else ""
    ]
    vf = ",".join([f for f in filters if f])

    # Определим расширения
    video_exts = ('.mp4', '.mov', '.avi', '.mkv')
    image_exts = ('.jpg', '.jpeg', '.png', '.webp')

    is_video = input_path.suffix.lower() in video_exts

    # ✨ Если видео и не .mp4 — сохраняем в .mp4
    if is_video and output_path.suffix.lower() != '.mp4':
        output_path = output_path.with_suffix('.mp4')

    # Если файл уже есть — удалим
    if output_path.exists():
        output_path.unlink()

    # 📼 Команда ffmpeg
    cmd = [
        'ffmpeg', '-y', '-i', str(input_path),
        '-vf', vf
    ]

    if is_video:
        if fps_change:
            cmd += ['-r', str(fps_change)]
        cmd += ['-c:a', 'aac']  # перекодируем аудио, для mp4 стабильнее
    cmd.append(str(output_path))

    print(f"Running command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print(f"✅ Media saved to: {output_path}")
    return str(output_path)

def convert_to_mp4(input_path: str, output_path: str = None) -> str:
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"❌ Input file not found: {input_path}")

    # Автоматически задаём путь, если не указан
    if output_path is None:
        output_path = input_path.with_suffix('.mp4')
    else:
        output_path = Path(output_path)

    # Команда для конвертации
    cmd = [
        'ffmpeg',
        '-y',  # overwrite without asking
        '-i', str(input_path),  # input file
        '-c:v', 'libx264',  # видео кодек (совместим с большинством устройств)
        '-crf', '23',  # качество (меньше = лучше, 18–28 норм)
        '-preset', 'medium',  # скорость/качество
        '-c:a', 'aac',  # аудиокодек
        '-b:a', '128k',  # аудиокачество
        str(output_path)
    ]

    print(f"🔄 Converting {input_path.name} → {output_path.name}")
    subprocess.run(cmd, check=True)
    print(f"✅ Saved: {output_path}")

    return str(output_path)

