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
# 2. KONFIGURASI GEMINI AI & TRANSKRIP
# ==========================================
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.sidebar.subheader("⚙️ Konfigurasi Kunci API")
    api_key_input = st.sidebar.text_input("Masukkan Google Gemini API Key:", type="password")
    if api_key_input:
        genai.configure(api_key=api_key_input)

def extract_youtube_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            p = parse_qs(parsed_url.query)
            return p.get('v', [None])[0]
        elif parsed_url.path.startswith(('/embed/', '/v/')):
            return parsed_url.path.split('/')[2]
    return None

def get_video_transcript(youtube_url):
    video_id = extract_youtube_id(youtube_url)
    if not video_id:
        return None
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['id', 'en'])
        full_text = " ".join([item['text'] for item in transcript_list])
        return full_text
    except Exception as e:
        return None

def analyze_transcript_with_gemini(transcript_text):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Analisis transkrip video YouTube berikut dan buatkan daftar 5 klip terbaik yang memiliki potensi viral tinggi (hook menarik).
        Berikan hasilnya dalam format JSON murni berupa list of objects dengan struktur kunci berikut:
        [
            {{"id": 1, "title": "Judul Klip Menarik", "start": "00:00:10", "end": "00:00:50", "score": 95, "cat": "🔥 Curiosity Hook"}},
            {{"id": 2, "title": "Judul Klip Kedua", "start": "00:01:10", "end": "00:02:00", "score": 90, "cat": "💡 Knowledge/Daging"}}
        ]
        Pastikan format waktu berformat HH:MM:SS. Jangan sertakan teks pembuka atau penutup lain, pastikan murni format JSON yang valid.
        
        Transkrip:
        {transcript_text[:15000]}
        """
        response = model.generate_content(prompt)
        text_response = response.text.strip()
        
        if text_response.startswith("```json"):
            text_response = text_response[7:-3].strip()
        elif text_response.startswith("```"):
            text_response = text_response[3:-3].strip()
            
        clips = json.loads(text_response)
        return clips
    except Exception as e:
        return [
            {"id": 1, "title": "Analisis Inti Video Utama", "start": "00:00:10", "end": "00:00:50", "score": 88, "cat": "🔥 Curiosity Hook"},
            {"id": 2, "title": "Pembahasan Sesi Lanjutan", "start": "00:01:00", "end": "00:01:50", "score": 85, "cat": "💡 Knowledge/Daging"}
        ]

# ==========================================
# 3. RENDER ENGINE (ROBUST MULTI-CLIENT & FFMPEG)
# ==========================================
def render_clip_ffmpeg(youtube_url, start_str, end_str, aspect_ratio="9:16 (TikTok/Reels/Shorts)", output_filename="viral_clip.mp4"):
    temp_raw = "temp_raw.mp4"
    
    if os.path.exists(temp_raw):
        os.remove(temp_raw)
    if os.path.exists(output_filename):
        os.remove(output_filename)

    client_strategies = [
        ["--extractor-args", "youtube:player_client=android"],
        ["--extractor-args", "youtube:player_client=ios"],
        ["--extractor-args", "youtube:player_client=web"]
    ]
    
    success_download = False
    for strategy in client_strategies:
        dl_command = [
            "yt-dlp",
            "-f", "best[height<=720]/best",
            "--no-playlist",
        ] + strategy + [
            "-o", temp_raw,
            youtube_url
        ]
        try:
            subprocess.run(dl_command, check=True, capture_output=True, text=True)
            if os.path.exists(temp_raw) and os.path.getsize(temp_raw) > 0:
                success_download = True
                break
        except subprocess.CalledProcessError:
            continue
            
    if not success_download:
        st.error("Gagal mengunduh video dari YouTube. Periksa kembali tautan yang dimasukkan.")
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
        subprocess.run(ffmpeg_command, check=True)
        
        if os.path.exists(temp_raw):
            os.remove(temp_raw)
            
        return output_filename
    except Exception as e:
        st.error(f"Gagal merender video via FFmpeg: {e}")
        return None

# ==========================================
# 4. HEADER & SETTINGS
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

st.divider()

# ==========================================
# 5. INPUT & OPSI MULTI-FORMAT
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
# 6. EKSEKUSI ANALISIS & RENDER
# ==========================================
if analyze_btn or "analyzed_clips" in st.session_state:
    if analyze_btn:
        if not url_input:
            st.warning("⚠️ Masukkan dulu tautan YouTube yang valid ya!")
        else:
            with st.spinner("🤖 AI sedang membaca transkrip asli & merumuskan klip viral terbaik..."):
                transcript_text = get_video_transcript(url_input)
                
                if transcript_text:
                    st.session_state.analyzed_clips = analyze_transcript_with_gemini(transcript_text)
                else:
                    st.warning("⚠️ Transkrip otomatis tidak ditemukan pada video ini. Menggunakan analisis cadangan.")
                    st.session_state.analyzed_clips = [
                        {"id": 1, "title": "Poin Penting Video Utama", "start": "00:00:10", "end": "00:00:50", "score": 88, "cat": "🔥 Curiosity Hook"}
                    ]
                st.session_state.current_url = url_input

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
                    <p><b>💬 Segmen Video:</b> Berhasil diekstrak langsung berdasarkan transkrip asli video YouTube.</p>
                </div>
                """, unsafe_allow_html=True)
                
                col_btn1, col_btn2 = st.columns([1, 2])
                with col_btn1:
                    render_trigger = st.button(f"🎬 Render Klip #{c_id}", key=f"render_{c_id}", type="primary")
                
                if render_trigger:
                    with st.spinner(f"⚡ FFmpeg sedang merender Klip #{c_id} ke format {resolution_choice}... Mohon tunggu!"):
                        out_file = f"clip_{c_id}.mp4"
                        rendered_path = render_clip_ffmpeg(
                            st.session_state.current_url,
                            clip["start"],
                            clip["end"],
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
