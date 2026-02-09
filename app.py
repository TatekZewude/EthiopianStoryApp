import streamlit as st
import os
import random
import subprocess
from gtts import gTTS
from moviepy.editor import (
    AudioFileClip,
    ImageClip,
    VideoFileClip,
    TextClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips
)
from moviepy.video.VideoClip import ColorClip

# =========================
# 1. SYSTEM PROMPTS
# =========================
SYSTEM_PROMPTS = {
    "Young Man": "Restless, fast-talking, loves Addis Ababa's lights, uses technology slang.",
    "Old Man": "Calm, slow, loves the soil of the village, speaks in proverbs."
}

# =========================
# 2. PATHS & ASSETS
# =========================
BASE_DIR = os.getcwd()
FONT_PATH = os.path.join(BASE_DIR, "AbyssinicaSIL-Regular.ttf")

CITY_BG = os.path.join(BASE_DIR, "city_bg.png")
VILLAGE_BG = os.path.join(BASE_DIR, "village_bg.png")
NARRATOR_BG = os.path.join(BASE_DIR, "narrator_bg.png")

YOUNG_FACE = os.path.join(BASE_DIR, "young_face.png")
OLD_FACE = os.path.join(BASE_DIR, "old_face.png")

TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# =========================
# 3. VIDEO SETTINGS (VERTICAL 9:16)
# =========================
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# =========================
# 4. WAV2LIP (OPTIONAL)
# =========================
def run_wav2lip(face_path, audio_path, output_path):
    cmd = [
        "python",
        "Wav2Lip/inference.py",
        "--checkpoint_path",
        "Wav2Lip/checkpoints/wav2lip_gan.pth",
        "--face",
        face_path,
        "--audio",
        audio_path,
        "--outfile",
        output_path,
        "--nosmooth"
    ]
    subprocess.run(cmd, check=True)
    return output_path

# =========================
# 5. HELPERS
# =========================
def apply_shake(clip):
    return clip.set_position(
        lambda t: (
            150 + random.uniform(-4, 4),
            200 + random.uniform(-4, 4)
        )
    )

def safe_image_clip(path, duration, resize_height):
    """
    Returns ImageClip if file exists, otherwise a solid color fallback
    """
    if os.path.exists(path):
        return ImageClip(path).set_duration(duration).resize(height=resize_height)
    else:
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0,0,0)).set_duration(duration)

# =========================
# 6. BUILD EPISODE
# =========================
def build_episode(narrator_text, dialogue_scenes):
    """
    narrator_text: string
    dialogue_scenes: list of (speaker, text) tuples
    """
    scenes = []

    # ---- A. Narrator scene
    narrator_audio_path = os.path.join(TEMP_DIR, "narrator.mp3")
    gTTS(text=narrator_text, lang="am").save(narrator_audio_path)
    narrator_audio = AudioFileClip(narrator_audio_path)

    narrator_bg = safe_image_clip(NARRATOR_BG, narrator_audio.duration, VIDEO_HEIGHT)

    subtitle = (
        TextClip(
            narrator_text,
            font=FONT_PATH,
            fontsize=60,
            color="yellow",
            stroke_color="black",
            stroke_width=2,
            method="caption",
            size=(VIDEO_WIDTH - 160, None)
        )
        .set_position("center")
        .set_duration(narrator_audio.duration)
    )

    scene = CompositeVideoClip([narrator_bg, subtitle]).set_audio(narrator_audio)
    scenes.append(scene)

    # ---- B. Dialogue scenes
    for i, (speaker, text) in enumerate(dialogue_scenes):
        audio_path = os.path.join(TEMP_DIR, f"voice_{i}.mp3")
        gTTS(text=text, lang="am").save(audio_path)
        audio_clip = AudioFileClip(audio_path)

        bg_img = CITY_BG if speaker == "Young Man" else VILLAGE_BG
        bg_clip = safe_image_clip(bg_img, audio_clip.duration, VIDEO_HEIGHT)

        face_img = YOUNG_FACE if speaker == "Young Man" else OLD_FACE
        char_clip = safe_image_clip(face_img, audio_clip.duration, 500)

        if speaker == "Young Man":
            char_clip = apply_shake(char_clip)
        else:
            char_clip = char_clip.set_position((600, 200))

        subtitle = (
            TextClip(
                text,
                font=FONT_PATH,
                fontsize=52,
                color="yellow",
                stroke_color="black",
                stroke_width=2,
                method="caption",
                size=(VIDEO_WIDTH - 160, None)
            )
            .set_position("center")
            .set_duration(audio_clip.duration)
        )

        scene = CompositeVideoClip([bg_clip, char_clip, subtitle]).set_audio(audio_clip)
        scenes.append(scene)

    # ---- C. Final video
    final_video = concatenate_videoclips(scenes, method="compose")

    # ---- D. Optional background radio music
    radio_bgm_path = os.path.join(BASE_DIR, "radio_bgm.mp3")
    if os.path.exists(radio_bgm_path):
        bgm = (
            AudioFileClip(radio_bgm_path)
            .volumex(0.10)
            .set_duration(final_video.duration)
        )
        final_audio = CompositeAudioClip([final_video.audio, bgm])
        final_video = final_video.set_audio(final_audio)

    # ---- E. Export
    output = os.path.join(BASE_DIR, "final_production.mp4")
    final_video.write_videofile(output, fps=24, codec="libx264", audio_codec="aac")
    return output

# =========================
# 7. STREAMLIT UI
# =========================
st.set_page_config(page_title="AI Cartoon Studio 🇪🇹", layout="centered")
st.markdown("<style>.stApp { background-color: #009B3A; color: white; }</style>", unsafe_allow_html=True)
st.title("🇪🇹 AI Cartoon Studio — Manual Scenes")

# ---- Episode number
episode_number = st.number_input("📻 Episode Number", min_value=1, step=1, value=1)

# ---- Narrator text
narrator_text = st.text_area("Narrator Text", "Welcome to Ethiopian Radio Story Episode 1")

# ---- Session state for manual dialogue scenes
if "scenes" not in st.session_state:
    st.session_state.scenes = []

# ---- Add dialogue scene
st.subheader("📝 Add Dialogue Scene")
speaker = st.text_input("Speaker Name", key="speaker_input")
dialogue = st.text_input("Dialogue Text", key="dialogue_input")

if st.button("➕ Add Scene"):
    if speaker and dialogue:
        st.session_state.scenes.append((speaker, dialogue))
        st.success(f"Scene added: {speaker} → {dialogue}")
        st.session_state.speaker_input = ""
        st.session_state.dialogue_input = ""

# ---- Show all added scenes
if st.session_state.scenes:
    st.subheader("🎬 Current Episode Scenes")
    for i, (spk, txt) in enumerate(st.session_state.scenes, 1):
        st.write(f"{i}. {spk}: {txt}")

# ---- Produce episode button
if st.button("🎬 Produce Episode", key="produce_button"):
    if not st.session_state.scenes:
        st.warning("Please add at least one dialogue scene!")
    else:
        with st.spinner("Producing radio episode..."):
            full_narration = f"ይህ የኢትዮጵያ ሬዲዮ ታሪክ ክፍል {episode_number} ነው። {narrator_text}"
            video_path = build_episode(full_narration, st.session_state.scenes)
        st.success("Episode created successfully!")
        st.video(video_path)
