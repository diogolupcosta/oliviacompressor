import os
import re
import json
import base64
import tempfile
import subprocess
from pathlib import Path

import streamlit as st


APP_NAME = "Olívia Claquete Crompress"
BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "logo.png"


# =========================
# Utils
# =========================
def run_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    return p.returncode, out, err


def ffmpeg_exists():
    return run_cmd(["ffmpeg", "-version"])[0] == 0


def ffprobe_json(path):
    cmd = [
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        path
    ]
    code, out, err = run_cmd(cmd)
    if code != 0:
        raise RuntimeError(err)
    return json.loads(out)


def human_size(num):
    for unit in ["B", "KB", "MB", "GB"]:
        if num < 1024:
            return f"{num:.2f} {unit}"
        num /= 1024
    return f"{num:.2f} TB"


def b64_image(path):
    return base64.b64encode(path.read_bytes()).decode()


def run_ffmpeg_with_progress(cmd, total_duration, progress_bar, status_text):
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    pattern = re.compile(r"out_time_ms=(\d+)")

    for line in process.stdout:
        match = pattern.search(line)
        if match:
            out_ms = int(match.group(1))
            out_sec = out_ms / 1_000_000
            progress = min(out_sec / total_duration, 1.0)

            progress_bar.progress(progress)
            status_text.text(
                f"Processando: {progress*100:.1f}% "
                f"({out_sec:.1f}s / {total_duration:.1f}s)"
            )

    process.wait()

    if process.returncode != 0:
        raise RuntimeError("Erro durante a compressão")


# =========================
# Streamlit setup
# =========================
st.set_page_config(APP_NAME, "🎬", layout="centered")

logo_b64 = b64_image(LOGO_PATH) if LOGO_PATH.exists() else ""

st.markdown("""
<style>
body, .stApp {
    background-color: #000000;
    color: #FFFFFF;
}
.card {
    background: linear-gradient(180deg, #0f0f0f, #000000);
    border-radius: 18px;
    padding: 20px;
    border: 1px solid rgba(139,92,246,0.35);
    box-shadow: 0 0 25px rgba(139,92,246,0.15);
    margin-bottom: 16px;
}
.header {
    display: flex;
    align-items: center;
    gap: 14px;
}
.logo {
    width: 56px;
    height: 56px;
    border-radius: 14px;
    border: 2px solid #8B5CF6;
    overflow: hidden;
}
.logo img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}
.title {
    font-size: 26px;
    font-weight: 800;
    color: #A78BFA;
    margin: 0;
}
.subtitle {
    font-size: 14px;
    color: #D1D5DB;
}
.stButton button {
    background-color: #7C3AED !important;
    color: white !important;
    border-radius: 14px !important;
}
div[role="progressbar"] > div {
    background-color: #8B5CF6 !important;
}
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# =========================
# Header
# =========================
st.markdown(f"""
<div class="card">
  <div class="header">
    <div class="logo">
      <img src="data:image/png;base64,{logo_b64}">
    </div>
    <div>
      <p class="title">{APP_NAME}</p>
      <p class="subtitle">
        Compressão focada em velocidade e qualidade para YouTube | by Diogo, o rei.
      </p>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


if not ffmpeg_exists():
    st.error("FFmpeg não encontrado no sistema.")
    st.stop()


# =========================
# Upload
# =========================
st.markdown('<div class="card">', unsafe_allow_html=True)
uploaded = st.file_uploader("Envie um vídeo MP4", type=["mp4"])
st.markdown('</div>', unsafe_allow_html=True)


if uploaded:
    tmp = tempfile.mkdtemp()
    input_path = os.path.join(tmp, uploaded.name)
    with open(input_path, "wb") as f:
        f.write(uploaded.getbuffer())

    meta = ffprobe_json(input_path)
    duration = float(meta["format"]["duration"])
    size_in = os.path.getsize(input_path)

    video_stream = next(
        s for s in meta["streams"] if s["codec_type"] == "video")
    width = int(video_stream["width"])
    height = int(video_stream["height"])

    st.markdown(f"""
    <div class="card">
      <b>Tamanho original:</b> {human_size(size_in)}<br>
      <b>Resolução:</b> {width}×{height}<br>
      <b>Duração:</b> {duration:.1f}s
    </div>
    """, unsafe_allow_html=True)

    # =========================
    # Settings
    # =========================
    st.markdown('<div class="card">', unsafe_allow_html=True)

    preset = st.selectbox(
        "Perfil",
        [
            "YouTube 1080p (recomendado)",
            "YouTube 720p",
            "Manter original"
        ]
    )

    crf = st.slider("Qualidade (CRF)", 18, 28, 22)
    speed = st.selectbox("Velocidade", ["fast", "medium"], index=0)
    audio = st.selectbox("Áudio kbps", [128, 160, 192], index=1)

    st.markdown('</div>', unsafe_allow_html=True)

    # =========================
    # Scale inteligente
    # =========================
    scale = None
    if preset == "YouTube 1080p (recomendado)" and height > 1080:
        scale = "scale=-2:1080"
    elif preset == "YouTube 720p" and height > 720:
        scale = "scale=-2:720"

    vf = ["-vf", scale] if scale else []

    output_path = os.path.join(tmp, f"compressed_{uploaded.name}")

    # =========================
    # Run
    # =========================
    if st.button("🎬 Comprimir vídeo"):
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-progress", "pipe:1",
            "-nostats",
            *vf,
            "-c:v", "libx264",
            "-preset", speed,
            "-crf", str(crf),
            "-profile:v", "high",
            "-level", "4.2",
            "-pix_fmt", "yuv420p",
            "-g", "60",
            "-keyint_min", "60",
            "-sc_threshold", "0",
            "-x264-params", "ref=4:bframes=3:aq-mode=2:aq-strength=1.0",
            "-threads", str(os.cpu_count()),
            "-c:a", "aac",
            "-b:a", f"{audio}k",
            "-movflags", "+faststart",
            output_path
        ]

        st.markdown('<div class="card">', unsafe_allow_html=True)
        bar = st.progress(0.0)
        status = st.empty()

        run_ffmpeg_with_progress(cmd, duration, bar, status)

        bar.progress(1.0)
        status.text("Compressão finalizada ✅")
        st.markdown('</div>', unsafe_allow_html=True)

        size_out = os.path.getsize(output_path)

        st.markdown(f"""
        <div class="card">
          <b>Tamanho final:</b> {human_size(size_out)}<br>
          <b>Redução:</b> {(1 - size_out/size_in)*100:.1f}%
        </div>
        """, unsafe_allow_html=True)

        with open(output_path, "rb") as f:
            st.download_button(
                "⬇️ Baixar vídeo comprimido",
                f,
                file_name=os.path.basename(output_path),
                mime="video/mp4"
            )

else:
    st.info("Envie um vídeo para começar.")
