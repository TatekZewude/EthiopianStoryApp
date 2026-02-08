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

# =========================
# 1. PATHS & ASSETS
# =========================
BASE_DIR = os.getcwd()
FONT_PATH = os.path.join(BASE_DIR, "AbyssinicaSIL-Regular.ttf")

CITY_BG = "city_bg.png"
VILLAGE_BG = "village_bg.png"
NARRATOR_BG = "narrator_bg.png"

YOUNG_FACE = "young_face.png"
OLD_FACE = "old_face.png"

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# =========================
# 2. VOICE PROFILES
# =========================
VOICE_PROFILES = {
    "Narrator": {"lang": "am", "tld": "com"},
    "Young Man": {"lang": "am", "tld": "com"},
    "Old Man": {"lang": "am", "tld": "co.uk"},
}

# =========================
# 3. HELPER FUNCTIONS
# =========================
def apply_shake(clip):
    return clip.set_position(
        lambda t: (
            VIDEO_WIDTH // 4 + random.uniform(-10, 10),
            VIDEO_HEIGHT // 2 - 250 + random.uniform(-10, 10)
        )
    )

def generate_voice(text, character, idx):
    profile = VOICE_PROFILES.get(character, VOICE_PROFILES["Narrator"])
    audio_path = f"{TEMP_DIR}/{character}_{idx}.mp3"
    gTTS(text=text, lang=profile["lang"], tld=profile["tld"]).save(audio_path)
    return AudioFileClip(audio_path)

def run_wav2lip(face_img, audio_clip_path, output_path):
    if not os.path.exists("Wav2Lip/checkpoints/wav2lip_gan.pth"):
        return None
    cmd = [
        "python",
        "Wav2Lip/inference.py",
        "--checkpoint_path",
        "Wav2Lip/checkpoints/wav2lip_gan.pth",
        "--face",
        face_img,
        "--audio",
        audio_clip_path,
        "--outfile",
        output_path,
        "--nosmooth"
    ]
    subprocess.run(cmd, check=True)
    return output_path

# =========================
# 4. BUILD EPISODE FUNCTION
# =========================
def build_episode(episode_number, chapter_number, episode_title, scenes_data):
    scenes = []

    for scene_idx, scene_data in enumerate(scenes_data):
        # -------------------------
        # Narrator intro
        # -------------------------
        narrator_text = scene_data.get("narrator", "")
        if narrator_text:
            narrator_audio = generate_voice(narrator_text, "Narrator", scene_idx)
            narrator_bg = ImageClip(NARRATOR_BG).set_duration(narrator_audio.duration).resize(height=VIDEO_HEIGHT)
            narrator_sub = TextClip(
                narrator_text,
                font=FONT_PATH,
                fontsize=50,
                color="white",
                stroke_color="black",
                stroke_width=3,
                method="label"
            ).set_position(("center", VIDEO_HEIGHT - 300)).set_duration(narrator_audio.duration)
            narrator_scene = CompositeVideoClip([narrator_bg, narrator_sub]).set_audio(narrator_audio)
            scenes.append(narrator_scene)

        # -------------------------
        # Character dialogues
        # -------------------------
        for i, (role, text) in enumerate(scene_data.get("dialogues", [])):
            audio_clip = generate_voice(text, role, scene_idx*10 + i)
            bg_img = CITY_BG if role == "Young Man" else VILLAGE_BG
            bg_clip = ImageClip(bg_img).set_duration(audio_clip.duration).resize(height=VIDEO_HEIGHT)

            # Lip-sync
            face_img = YOUNG_FACE if role == "Young Man" else OLD_FACE
            lipsync_output = f"{TEMP_DIR}/{role}_{scene_idx}_{i}_lipsync.mp4"
            if os.path.exists("Wav2Lip/checkpoints/wav2lip_gan.pth"):
                try:
                    run_wav2lip(face_img, audio_clip.filename, lipsync_output)
                    char_clip = VideoFileClip(lipsync_output).set_duration(audio_clip.duration).resize(height=500)
                except:
                    char_clip = ImageClip(face_img).set_duration(audio_clip.duration).resize(height=500)
            else:
                char_clip = ImageClip(face_img).set_duration(audio_clip.duration).resize(height=500)

            if role == "Young Man":
                char_clip = apply_shake(char_clip)
            else:
                char_clip = char_clip.set_position((VIDEO_WIDTH * 3 // 4 - 250, VIDEO_HEIGHT // 2 - 250))

            subtitle = TextClip(
                text,
                font=FONT_PATH,
                fontsize=50,
                color="yellow",
                stroke_color="black",
                stroke_width=3,
                method="label"
            ).set_position(("center", VIDEO_HEIGHT - 300)).set_duration(audio_clip.duration)

            scene_clip = CompositeVideoClip([bg_clip, char_clip, subtitle]).set_audio(audio_clip)
            scenes.append(scene_clip)

    # -------------------------
    # Final Video
    # -------------------------
    final_video = concatenate_videoclips(scenes, method="compose")

    # Optional BGM
    if os.path.exists("masinqo_bgm.mp3"):
        bgm = AudioFileClip("masinqo_bgm.mp3").volumex(0.12).set_duration(final_video.duration)
        final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bgm]))

    output = f"episode_{episode_number:02d}_chapter_{chapter_number:02d}.mp4"
    final_video.write_videofile(
        output,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="ultrafast",
        ffmpeg_params=["-pix_fmt", "yuv420p"]
    )
    return output

# =========================
# 5. STREAMLIT UI
# =========================
st.set_page_config(page_title="AI Radio Drama 🇪🇹", layout="centered")

st.title("🇪🇹 Ethiopian AI Radio Drama")
st.write("Old-style radio narration • Modern storytelling")

st.subheader("📘 Episode Details")
episode_number = st.number_input("Episode Number", min_value=1, step=1, value=1)
chapter_number = st.number_input("Chapter Number", min_value=1, step=1, value=1)
episode_title = st.text_input("Episode Title", "The Road Between City and Soil")

# -------------------------
# Session state for dynamic scenes
# -------------------------
if "scenes" not in st.session_state:
    st.session_state.scenes = []

# -------------------------
# Add a new scene
# -------------------------
st.subheader("➕ Add a New Scene")
with st.form(key=f"scene_form_{len(st.session_state.scenes)}"):
    narrator_text = st.text_area("Narrator text", key=f"narrator_{len(st.session_state.scenes)}")
    dialogues = []
    num_dialogues = st.number_input(
        "Number of dialogues in this scene", min_value=1, max_value=5, step=1, key=f"num_dialogues_{len(st.session_state.scenes)}"
    )
    for i in range(num_dialogues):
        col1, col2 = st.columns([1, 4])
        with col1:
            role = st.selectbox("Character", ["Young Man", "Old Man"], key=f"role_{len(st.session_state.scenes)}_{i}")
        with col2:
            text = st.text_input("Dialogue text", key=f"text_{len(st.session_state.scenes)}_{i}")
        dialogues.append((role, text))
    submitted = st.form_submit_button("Add Scene")
    if submitted:
        st.session_state.scenes.append({
            "narrator": narrator_text,
            "dialogues": dialogues
        })
        st.success(f"Scene {len(st.session_state.scenes)} added!")

# -------------------------
# Display & manage scenes
# -------------------------
if st.session_state.scenes:
    st.subheader("📝 Current Scenes (Editable & Reorderable)")

    for idx, scene in enumerate(st.session_state.scenes):
        st.markdown(f"### Scene {idx+1}")
        # Narrator edit
        scene['narrator'] = st.text_area(
            "Narrator text",
            value=scene['narrator'],
            key=f"edit_narrator_{idx}"
        )
        # Dialogues edit
        for i, (role, text) in enumerate(scene["dialogues"]):
            col1, col2 = st.columns([1, 4])
            with col1:
                new_role = st.selectbox(
                    "Character",
                    ["Young Man", "Old Man"],
                    index=["Young Man","Old Man"].index(role),
                    key=f"edit_role_{idx}_{i}"
                )
            with col2:
                new_text = st.text_input(
                    "Dialogue text",
                    value=text,
                    key=f"edit_text_{idx}_{i}"
                )
            scene["dialogues"][i] = (new_role, new_text)

        # Move Up / Move Down / Delete
        col_up, col_down, col_del = st.columns([1,1,1])
        with col_up:
            if st.button("⬆️ Move Up", key=f"moveup_{idx}") and idx > 0:
                st.session_state.scenes[idx-1], st.session_state.scenes[idx] = st.session_state.scenes[idx], st.session_state.scenes[idx-1]
                st.experimental_rerun()
        with col_down:
            if st.button("⬇️ Move Down", key=f"movedown_{idx}") and idx < len(st.session_state.scenes)-1:
                st.session_state.scenes[idx+1], st.session_state.scenes[idx] = st.session_state.scenes[idx], st.session_state.scenes[idx+1]
                st.experimental_rerun()
        with col_del:
            if st.button("❌ Delete Scene", key=f"delete_{idx}"):
                st.session_state.scenes.pop(idx)
                st.experimental_rerun()

# -------------------------
# Produce Episode
# -------------------------
if st.session_state.scenes:
    if st.button("🎬 Produce Episode"):
        with st.spinner("Rendering your AI radio episode..."):
            video = build_episode(
                episode_number,
                chapter_number,
                episode_title,
                st.session_state.scenes
            )
            st.video(video)
