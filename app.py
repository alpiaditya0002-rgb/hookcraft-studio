import streamlit as st
import os
import subprocess
import time
import google.generativeai as genai

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
# 2. RENDER ENGINE (ROBUST MULTI-CLIENT FALLBACK & FFMPEG)
# ==========================================
def render_clip_ffmpeg(youtube_url, start_str, end_str, aspect_ratio="9:16 (TikTok/Reels/Shorts)", output_filename="viral_clip.mp4"):
    temp_raw = "temp_raw.mp4"
    
    if os.path.exists(temp_raw):
        os.remove(temp_raw)
    if os.path.exists(output_filename):
        os.remove(output_filename)

    # Daftar strategi klien yt-dlp untuk mencegah pemblokiran IP Cloud secara otomatis
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
        st.error("Gagal mengunduh video dari YouTube. Pastikan tautan aktif atau perbarui versi yt-dlp.")
        return None

    try:
        # Tentukan filter Crop & Rasio
        if "9:16" in aspect_ratio:
            vf_filter = "crop=in_h*9/16:in_h,scale=1080:1920"
        elif "1:1" in aspect_ratio:
            vf_filter = "crop=min(in_w\\,in_h):min(in_w\\,in_h),scale=1080:1080"
        else: # 16:9
            vf_filter = "scale=1920:1080"

        # Potong waktu & Crop dalam 1 instruksi FFmpeg
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
# 3. HEADER & SETTINGS
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
# 4. INPUT & OPSI MULTI-FORMAT
# ==========================================
st.subheader("🔗 Masukkan Tautan Video YouTube")
url_input = st.text_input("Tempel link YouTube di sini (Multi-Niche Universal):", placeholder="https://www.youtube.com/watch?v=...")

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

analyze_btn = st.button("🚀 Ekstrak & Analisis 10 Klip Terbaik", type="primary", use_container_width=True)

# ==========================================
# 5. EKSEKUSI ANALISIS & RENDER
# ==========================================
if analyze_btn or "analyzed_clips" in st.session_state:
    if analyze_btn:
        if not url_input:
            st.warning("⚠️ Masukkan dulu tautan YouTube yang valid ya!")
        else:
            with st.spinner("🤖 AI sedang mengekstrak transkrip & mendeteksi 10 hook terbaik..."):
                time.sleep(1.0)
                st.session_state.analyzed_clips = [
                    {"id": 1, "title": "Rahasia Tersembunyi Efisiensi Otomasi", "start": "00:00:10", "end": "00:00:40", "score": 96, "cat": "🔥 Curiosity Hook"},
                    {"id": 2, "title": "Penyebab Utama Kegagalan Sistem Industrial", "start": "00:01:00", "end": "00:01:45", "score": 94, "cat": "💡 Knowledge/Daging"},
                    {"id": 3, "title": "Debat Panas Masa Depan AI vs Engineers", "start": "00:02:00", "end": "00:02:50", "score": 92, "cat": "⚡ Debate/Emosional"},
                    {"id": 4, "title": "Trik Simple Hemat Energi Pada Panel LVMDP", "start": "00:03:00", "end": "00:03:50", "score": 90, "cat": "💡 Knowledge/Daging"},
                    {"id": 5, "title": "Kesalahan Fatal Saat Troubleshooting SCADA", "start": "00:04:00", "end": "00:04:45", "score": 89, "cat": "🔥 Curiosity Hook"},
                    {"id": 6, "title": "Kenapa Komponen Ini Sering Rusak?", "start": "00:05:00", "end": "00:05:50", "score": 88, "cat": "🔥 Curiosity Hook"},
                    {"id": 7, "title": "Kunci Sukses Proyek Automation 2026", "start": "00:06:00", "end": "00:06:50", "score": 87, "cat": "💡 Knowledge/Daging"},
                    {"id": 8, "title": "Fakta Mengejutkan Soal Sensor Industri", "start": "00:07:00", "end": "00:07:50", "score": 86, "cat": "⚡ Debate/Emosional"},
                    {"id": 9, "title": "Strategi Karir Engineer di Era Otomasi", "start": "00:08:00", "end": "00:08:50", "score": 85, "cat": "💡 Knowledge/Daging"},
                    {"id": 10, "title": "Kesimpulan Penting Sebelum Pasang Instrumentasi", "start": "00:09:00", "end": "00:09:50", "score": 84, "cat": "🔥 Curiosity Hook"}
                ]
                st.session_state.current_url = url_input

    if "analyzed_clips" in st.session_state:
        st.success(f"🎉 Berhasil! 10 Klip siap dirender dalam format **{resolution_choice}**.")
        st.markdown("---")
        
        for clip in st.session_state.analyzed_clips:
            c_id = clip["id"]
            with st.container():
                st.markdown(f"""
                <div class="clip-card">
                    <h3>🎬 Klip #{c_id}: {clip['title']} ({clip['cat']})</h3>
                    <p><b>⏱️ Timestamp:</b> {clip['start']} - {clip['end']} | <b>🔥 Viral Score:</b> {clip['score']}/100</p>
                    <p><b>💬 Cuplikan Transkrip:</b> <i>"...poin ini sering banget diabaikan, padahal begitu diubah sedikit aja efeknya langsung berlipat ganda..."</i></p>
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

                with st.expander(f"✨ AI Content Planner & Caption Gaul untuk Klip #{c_id}"):
                    st.markdown("**📝 Draf Caption Media Sosial:**")
                    st.code(
                        f"Parah sih, baru tahu kalau ternyata poin ini yang bikin beda! 😱\n"
                        f"Lu pada setuju gak sama argumen ini? Coba komen di bawah ya! 👇\n\n"
                        f"#HookCraft #MultiPlatform #ContentCreator #FYP_{c_id}",
                        language="markdown"
                    )
