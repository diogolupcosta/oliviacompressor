import os
import base64
import requests
from pathlib import Path

import streamlit as st


# =========================
# Config
# =========================
APP_NAME = "Olívia Claquete Crompress"
BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "logo.png"

API_URL = "https://3e26-177-37-181-2.ngrok-free.app/compress"


# =========================
# Utils
# =========================
def human_size(num):
    for unit in ["B", "KB", "MB", "GB"]:
        if num < 1024:
            return f"{num:.2f} {unit}"
        num /= 1024
    return f"{num:.2f} TB"


def b64_image(path):
    return base64.b64encode(path.read_bytes()).decode()


def compress_via_api(video_bytes, preset, crf):
    files = {
        "file": ("video.mp4", video_bytes, "video/mp4")
    }

    params = {
        "preset": preset,
        "crf": crf
    }

    response = requests.post(
        API_URL,
        files=files,
        params=params,
        timeout=900
    )

    if response.status_code != 200:
        raise RuntimeError(response.text)

    return response.content


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


# =========================
# Upload
# =========================
st.markdown('<div class="card">', unsafe_allow_html=True)
uploaded = st.file_uploader("Envie um vídeo MP4", type=["mp4"])
st.markdown('</div>', unsafe_allow_html=True)


if uploaded:
    size_in = len(uploaded.getvalue())

    st.markdown(f"""
    <div class="card">
      <b>Tamanho original:</b> {human_size(size_in)}
    </div>
    """, unsafe_allow_html=True)

    # =========================
    # Settings
    # =========================
    st.markdown('<div class="card">', unsafe_allow_html=True)

    preset_ui = st.selectbox(
        "Perfil",
        [
            "YouTube 1080p (recomendado)",
            "YouTube 720p",
            "Manter original"
        ]
    )

    crf = st.slider("Qualidade (CRF)", 18, 28, 22)
    speed = st.selectbox("Velocidade", ["fast", "medium"], index=0)

    st.caption("CRF: quanto MAIOR, mais compressão e menor o arquivo.")

    st.markdown('</div>', unsafe_allow_html=True)

    # =========================
    # Preset backend
    # =========================
    if preset_ui == "YouTube 1080p (recomendado)":
        preset_api = "1080p"
    elif preset_ui == "YouTube 720p":
        preset_api = "720p"
    else:
        preset_api = "original"

    # =========================
    # Run
    # =========================
    if st.button("🎬 Comprimir vídeo"):
        with st.spinner("Enviando para compressão no servidor..."):
            try:
                output_bytes = compress_via_api(
                    uploaded.getvalue(),
                    preset=preset_api,
                    crf=crf
                )
            except Exception as e:
                st.error(f"Erro na compressão: {e}")
                st.stop()

        size_out = len(output_bytes)

        st.success("Compressão finalizada ✅")

        st.markdown(f"""
        <div class="card">
          <b>Tamanho final:</b> {human_size(size_out)}<br>
          <b>Redução:</b> {(1 - size_out/size_in)*100:.1f}%
        </div>
        """, unsafe_allow_html=True)

        st.download_button(
            "⬇️ Baixar vídeo comprimido",
            output_bytes,
            file_name="compressed.mp4",
            mime="video/mp4"
        )

else:
    st.info("Envie um vídeo para começar.")
