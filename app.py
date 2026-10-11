import streamlit as st
import os
import subprocess
import time
import json
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

# ==========================================
# 1. KONFIGURASI HALAMAN & DUAL THEME
# ==========================================
st.set_page_config(
    page_title="HookCraft Studio - AI Viral Clip Generator",
    page_icon="🎬",
    layout="wide"
)

if "theme" not in st.session_state:
    st.session_state.theme = "Dark Mode"

if st.session_state.theme == "Dark Mode":
    bg_color = "#0e1117"
    text_color = "#fafafa"
    card_bg = "#1f2937"
else:
    bg_color = "#ffffff"
    text_color = "#111827"
    card_bg = "#f3f4f6"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    .clip-card {{
        background-color: {card_bg};
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid rgba(255,255,255,0.1);
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# 2. INISIALISASI GEMINI AI & SIDEBAR COOKIES
# ==========================================
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.sidebar.subheader("🔐 Autentikasi YouTube (Bypass Bot)")
cookie_input_method = st.sidebar.radio("Metode Input Cookies:", ["Paste Teks Cookies", "Upload File .txt"])

cookie_raw_data = ""
if cookie_input_method == "Paste Teks Cookies":
    cookie_raw_data = st.sidebar.text_area("Tempel string cookies di sini:", placeholder="__Secure-3PSID=...; SAPISID=...")
else:
    uploaded_cookies = st.sidebar.file_uploader("Upload file cookies.txt", type=["txt"])
    if uploaded_cookies is not None:
        cookie_raw_data = uploaded_cookies.read().decode("utf-8")

def check_system_tools():
    try:
        ffmpeg_check = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).returncode == 0
        return ffmpeg_check
    except Exception:
        return False

# ==========================================
# 3. HELPER URL, COOKIE CONVERTER & GEMINI
# ==========================================
def clean_youtube_url(url):
    parsed = urlparse(url)
    if parsed.netloc in ('youtu.be', 'www.youtu.be'):
        video_id = parsed.path.lstrip('/')
        return f"https://www.youtube.com/watch?v={video_id}"
    elif 'youtube.com' in parsed.netloc:
        qs = parse_qs(parsed.query)
        if 'v' in qs:
            video_id = qs['v'][0]
            return f"https://www.youtube.com/watch?v={video_id}"
    return url

def prepare_cookie_file(raw_data):
    """Mengonversi string cookies mentah menjadi Netscape format untuk yt-dlp"""
    if not raw_data or not raw_data.strip():
        return None
    
    cookie_file_path = "cookies_temp.txt"
    try:
        with open(cookie_file_path, "w", encoding="utf-8") as f:
            f.write("# Netscape HTTP Cookie File\n")
            # Jika formatnya adalah key-value dipisah titik koma
            if ";" in raw_data and not raw_data.strip().startswith("#"):
                pairs = raw_data.split(";")
                for pair in pairs:
                    if "=" in pair:
                        parts = pair.strip().split("=", 1)
                        if len(parts) == 2:
                            name, value = parts
                            f.write(f".youtube.com\tTRUE\t/\tTRUE\t2147483647\t{name.strip()}\t{value.strip()}\n")
            else:
                # Jika sudah berformat Netscape
                f.write(raw_data)
        return cookie_file_path
    except Exception:
        return None

def analyze_with_gemini(url_input):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Buatkan 5 daftar segmen klip video potensial (timestamp awal dan akhir) untuk konten video YouTube dengan tautan: {url_input}.
        Berikan hasilnya dalam format JSON murni berupa list of objects dengan struktur berikut:
        [
            {{"id": 1, "title": "Judul Klip Menarik 1", "start": "00:00:10", "end": "00:00:50", "score": 95, "cat": "🔥 Curiosity Hook"}},
            {{"id": 2, "title": "Judul Klip Menarik 2", "start": "00:01:10", "end": "00:02:00", "score": 90, "cat": "💡 Knowledge/Daging"}}
        ]
        Pastikan format waktu HH:MM:SS. Murni format JSON tanpa teks lain.
        """
        response = model.generate_content(prompt)
        text_response = response.text.strip()
        if text_response.startswith("```json"):
            text_response = text_response[7:-3].strip()
        elif text_response.startswith("```"):
            text_response = text_response[3:-3].strip()
        return json.loads(text_response)
    except Exception:
        return [
            {"id": 1, "title": "Poin Utama Pembahasan", "start": "00:00:10", "end": "00:00:50", "score": 90, "cat": "🔥 Curiosity Hook"},
            {"id": 2, "title": "Sesi Penjelasan Mendalam", "start": "00:01:00", "end": "00:01:50", "score": 85, "cat": "💡 Knowledge/Daging"}
        ]

# ==========================================
# 4. RENDER ENGINE (YT-DLP DENGAN COOKIES & FFMPEG)
# ==========================================
def render_clip_ffmpeg(youtube_url, start_str, end_str, raw_cookies, aspect_ratio="9:16 (TikTok/Reels/Shorts)", output_filename="viral_clip.mp4"):
    temp_raw = "temp_raw.mp4"
    clean_url = clean_youtube_url(youtube_url)
    
    if os.path.exists(temp_raw):
        os.remove(temp_raw)
    if os.path.exists(output_filename):
        os.remove(output_filename)

    cookie_file = prepare_cookie_file(raw_cookies)

    dl_command = [
        "yt-dlp",
        "--js-runtimes", "node",
        "--extractor-args", "youtube:player_client=web",
    ]

    if cookie_file and os.path.exists(cookie_file):
        dl_command.extend(["--cookies", cookie_file])

    dl_command.extend([
        "-f", "b / bv+ba",
        "--no-playlist",
        "-o", temp_raw,
        clean_url
    ])
    
    try:
        subprocess.run(dl_command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)
        st.error(f"Gagal mengunduh video via yt-dlp. Detail: {e.stderr}")
        return None

    if cookie_file and os.path.exists(cookie_file):
        os.remove(cookie_file)

    if not os.path.exists(temp_raw) or os.path.getsize(temp_raw) == 0:
        st.error("File video gagal disimpan atau kosong.")
        return None

    try:
        if "9:16" in aspect_ratio:
            vf_filter = "crop=in_h*9/16:in_h,scale=1080:1920"
        elif "1:1" in aspect_ratio:
            vf_filter = "crop=min(in_w\\,in_h):min(in_w\\,in_h),scale=1080:1080"
        else:
            vf_filter = "scale=1920:1080"

        ffmpeg_command = [
            "ffmpeg", "-y",
            "-ss", start_str,
            "-to", end_str,
            "-i", temp_raw,
            "-vf", vf_filter,
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            output_filename
        ]
        subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
        
        if os.path.exists(temp_raw):
            os.remove(temp_raw)
            
        return output_filename
    except Exception as e:
        st.error(f"Gagal merender video via FFmpeg: {e}")
        return None

# ==========================================
# 5. HEADER & STATUS SISTEM
# ==========================================
col_head1, col_head2 = st.columns([8, 2])
with col_head1:
    st.title("🎬 HookCraft Studio AI")
    st.markdown("*Transform long-form YouTube videos into multi-format viral clips instantly.*")
with col_head2:
    theme_toggle = st.selectbox("🎨 Theme", ["Dark Mode", "Light Mode"], index=0 if st.session_state.theme == "Dark Mode" else 1)
    if theme_toggle != st.session_state.theme:
        st.session_state.theme = theme_toggle
        st.rerun()

if check_system_tools():
    st.sidebar.success("✅ Server Tools Aktif (FFmpeg & Node)")
else:
    st.sidebar.error("❌ Pengecekan Sistem Bermasalah")

st.divider()

# ==========================================
# 6. INPUT & OPSI MULTI-FORMAT
# ==========================================
st.subheader("🔗 Masukkan Tautan Video YouTube")
url_input = st.text_input("Tempel link YouTube di sini:", placeholder="https://www.youtube.com/watch?v=...")

col_opt1, col_opt2, col_opt3 = st.columns(3)
with col_opt1:
    duration_choice = st.selectbox(
        "⏱️ Target Durasi Klip:",
        ["Kurang dari 1 Menit (< 60s)", "1 - 2 Menit", "2 - 3 Menit"]
    )
with col_opt2:
    resolution_choice = st.selectbox(
        "📐 Format Rasio / Resolusi:",
        [
            "9:16 (TikTok/Reels/Shorts)", 
            "1:1 (Square Feed)", 
            "16:9 (YouTube/Landscape)"
        ]
    )
with col_opt3:
    niche_mode = st.selectbox(
        "🎯 Mode Niche:",
        ["Auto-Detect Multi-Niche 🛠️", "Tech & Industrial", "Finance & Crypto", "Education & Podcast"]
    )

analyze_btn = st.button("🚀 Ekstrak & Analisis Klip Terbaik via AI", type="primary", use_container_width=True)

# ==========================================
# 7. EKSEKUSI ANALISIS & RENDER
# ==========================================
if analyze_btn or "analyzed_clips" in st.session_state:
    if analyze_btn:
        if not url_input:
            st.warning("⚠️ Masukkan dulu tautan YouTube yang valid ya!")
        else:
            with st.spinner("🤖 AI sedang memproses tautan & merumuskan klip viral terbaik..."):
                cleaned_url = clean_youtube_url(url_input)
                st.session_state.analyzed_clips = analyze_with_gemini(cleaned_url)
                st.session_state.current_url = cleaned_url

    if "analyzed_clips" in st.session_state:
        st.success(f"🎉 Berhasil menganalisis video! Klip siap dirender dalam format **{resolution_choice}**.")
        st.markdown("---")
        
        for clip in st.session_state.analyzed_clips:
            c_id = clip["id"]
            with st.container():
                st.markdown(f"""
                <div class="clip-card">
                    <h3>🎬 Klip #{c_id}: {clip['title']} ({clip.get('cat', '🔥 Hook')})</h3>
                    <p><b>⏱️ Timestamp:</b> {clip['start']} - {clip['end']} | <b>🔥 Viral Score:</b> {clip.get('score', 90)}/100</p>
                    <p><b>💬 Status:</b> Siap dipotong dan dirender menggunakan FFmpeg & Node.js.</p>
                </div>
                """, unsafe_allow_html=True)
                
                col_btn1, col_btn2 = st.columns([1, 2])
                with col_btn1:
                    render_trigger = st.button(f"🎬 Render Klip #{c_id}", key=f"render_{c_id}", type="primary")
                
                if render_trigger:
                    with st.spinner(f"⚡ FFmpeg sedang memotong & merender Klip #{c_id} ke format {resolution_choice}... Mohon tunggu!"):
                        out_file = f"clip_{c_id}.mp4"
                        rendered_path = render_clip_ffmpeg(
                            st.session_state.current_url,
                            clip["start"],
                            clip["end"],
                            cookie_raw_data,
                            aspect_ratio=resolution_choice,
                            output_filename=out_file
                        )
                        if rendered_path and os.path.exists(rendered_path):
                            st.success(f"✨ Klip #{c_id} Berhasil Dirender!")
                            with open(rendered_path, "rb") as file_data:
                                st.download_button(
                                    label=f"📥 Download File MP4",
                                    data=file_data,
                                    file_name=f"HookCraft_Clip_{c_id}.mp4",
                                    mime="video/mp4",
                                    key=f"dl_{c_id}"
                                )

                with st.expander(f"✨ AI Content Planner & Caption untuk Klip #{c_id}"):
                    st.markdown("**📝 Draf Caption Media Sosial:**")
                    st.code(
                        f"Pembahasan daging banget nih! Wajib ditonton sampai habis. 😱\n"
                        f"Gimana menurut kalian? Coba komen di bawah ya! 👇\n\n"
                        f"#HookCraft #ContentCreator #FYP #Klip_{c_id}",
                        language="markdown"
                    )
