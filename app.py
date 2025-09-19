"""
Streamlit Video Editor with Online Search (Pexels)

Files included in this single-file app:
- app.py (this file)

Requirements (paste into requirements.txt):
streamlit
moviepy
requests
Pillow
numpy
pydub
validators

Notes:
- This app uses the Pexels API for image and video search. Get a free API key from https://www.pexels.com/api/ and set it as an environment variable `PEXELS_API_KEY` or put it in Streamlit secrets under `PEXELS_API_KEY`.
- MoviePy requires ffmpeg installed on your system (install via apt, brew, or download from ffmpeg.org).
- This is a simple editor: you can search & add online images/videos, upload local files, trim, reorder, and export a combined video.

Run:
streamlit run streamlit_video_editor_app.py

"""

import streamlit as st
import requests
import os
import tempfile
from moviepy.editor import VideoFileClip, ImageClip, concatenate_videoclips, AudioFileClip
from PIL import Image
from io import BytesIO
import validators
import json

st.set_page_config(page_title="Streamlit Video Editor", layout="wide")

# ---------------------- Utility functions ----------------------
def get_pexels_api_key():
    # Priority: st.secrets -> env var
    key = None
    try:
        key = st.secrets["CdatHQezjqI1tA5zbPR6dlxFqRoBMBQ7DueRmPTCJCjs2kvRCPelckfE"]
    except Exception:
        key = os.environ.get("CdatHQezjqI1tA5zbPR6dlxFqRoBMBQ7DueRmPTCJCjs2kvRCPelckfE")
    return key

def pexels_search_images(query, per_page=8):
    api_key = get_pexels_api_key()
    if not api_key:
        st.error("Pexels API key not found. Set PEXELS_API_KEY in Streamlit secrets or env variables.")
        return []
    url = "https://api.pexels.com/v1/search"
    params = {"query": query, "per_page": per_page}
    headers = {"Authorization": api_key}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    if r.status_code != 200:
        st.warning(f"Pexels image search failed: {r.status_code}")
        return []
    data = r.json()
    return data.get("photos", [])

def pexels_search_videos(query, per_page=6):
    api_key = get_pexels_api_key()
    if not api_key:
        st.error("Pexels API key not found. Set PEXELS_API_KEY in Streamlit secrets or env variables.")
        return []
    url = "https://api.pexels.com/videos/search"
    params = {"query": query, "per_page": per_page}
    headers = {"Authorization": api_key}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    if r.status_code != 200:
        st.warning(f"Pexels video search failed: {r.status_code}")
        return []
    data = r.json()
    return data.get("videos", [])

def download_url_to_file(url, dest_path):
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return dest_path

# ---------------------- Session state ----------------------
if "timeline" not in st.session_state:
    st.session_state.timeline = []  # each item: dict {"type":"video"|"image","path":..., "start":0, "end":None}

if "counter" not in st.session_state:
    st.session_state.counter = 0

# ---------------------- UI ----------------------
st.title("📼 Streamlit Video Editor — Search & Edit")
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Search online")
    q = st.text_input("Search images/videos (Pexels)", key="search_q")
    per_page = st.slider("Results", min_value=4, max_value=20, value=8)
    search_type = st.radio("Type", ["Images", "Videos"], index=0)
    if st.button("Search"):
        if not q:
            st.warning("Type a search query first")
        else:
            with st.spinner("Searching Pexels..."):
                if search_type == "Images":
                    results = pexels_search_images(q, per_page=per_page)
                else:
                    results = pexels_search_videos(q, per_page=per_page)
            st.session_state.last_search = results

    if "last_search" in st.session_state and st.session_state.last_search:
        st.markdown("**Results**")
        results = st.session_state.last_search
        for i, r in enumerate(results):
            if search_type == "Images":
                thumb = r.get("src", {}).get("medium")
                st.image(thumb, width=200)
                if st.button(f"Add image {i}"):
                    # download best quality
                    img_url = r.get("src", {}).get("original")
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                    download_url_to_file(img_url, tmp.name)
                    st.session_state.timeline.append({"id": st.session_state.counter, "type": "image", "path": tmp.name, "duration": 3})
                    st.session_state.counter += 1
                    st.success("Image added to timeline")
            else:
                # videos
                thumb = r.get("image")
                st.image(thumb, width=250)
                # choose best file (highest width)
                video_files = r.get("video_files", [])
                if st.button(f"Add video {i}"):
                    # pick highest quality
                    chosen = sorted(video_files, key=lambda x: x.get("height", 0))[-1]
                    video_url = chosen.get("link")
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                    download_url_to_file(video_url, tmp.name)
                    st.session_state.timeline.append({"id": st.session_state.counter, "type": "video", "path": tmp.name, "start": 0, "end": None})
                    st.session_state.counter += 1
                    st.success("Video added to timeline")

    st.markdown("---")
    st.subheader("Upload local files")
    uploaded = st.file_uploader("Upload image/video files", accept_multiple_files=True)
    if uploaded:
        for f in uploaded:
            name = f.name
            suffix = name.split('.')[-1].lower()
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.' + suffix)
            tmp.write(f.getbuffer())
            tmp.flush()
            if suffix in ["png", "jpg", "jpeg", "gif"]:
                st.session_state.timeline.append({"id": st.session_state.counter, "type": "image", "path": tmp.name, "duration": 3})
            else:
                st.session_state.timeline.append({"id": st.session_state.counter, "type": "video", "path": tmp.name, "start": 0, "end": None})
            st.session_state.counter += 1
        st.success("Uploaded files added to timeline")

with col2:
    st.subheader("Timeline")
    if not st.session_state.timeline:
        st.info("No clips in timeline. Add search results or upload files from the left.")
    else:
        to_remove = None
        for idx, item in enumerate(st.session_state.timeline):
            st.markdown(f"**Clip {idx+1} — ({item['type']}) id={item['id']}**")
            st.write(item['path'])
            c1, c2, c3, c4 = st.columns([1,1,1,2])
            if item['type'] == 'video':
                if c1.button('Preview', key=f'preview_{item["id"]}'):
                    st.video(item['path'])
                start = c2.number_input('Start (s)', min_value=0.0, value=float(item.get('start',0)), key=f'start_{item["id"]}')
                end = c3.number_input('End (s or 0 for full)', min_value=0.0, value=float(item.get('end') or 0.0), key=f'end_{item["id"]}')
                item['start'] = start
                item['end'] = end if end>0 else None
            else:
                if c1.button('Preview', key=f'preview_img_{item["id"]}'):
                    st.image(item['path'])
                duration = c2.number_input('Duration (s)', min_value=0.5, value=float(item.get('duration',3)), key=f'dur_{item["id"]}')
                item['duration'] = duration
            if c4.button('Remove', key=f'remove_{item["id"]}'):
                to_remove = idx
            # reorder controls
            r1, r2 = st.columns([1,1])
            if r1.button('Move Up', key=f'moveup_{item["id"]}') and idx>0:
                st.session_state.timeline[idx-1], st.session_state.timeline[idx] = st.session_state.timeline[idx], st.session_state.timeline[idx-1]
            if r2.button('Move Down', key=f'movedown_{item["id"]}') and idx < len(st.session_state.timeline)-1:
                st.session_state.timeline[idx+1], st.session_state.timeline[idx] = st.session_state.timeline[idx], st.session_state.timeline[idx+1]
            st.markdown('---')
        if to_remove is not None:
            st.session_state.timeline.pop(to_remove)
            st.experimental_rerun()

st.sidebar.title("Export & Settings")
fps = st.sidebar.number_input("Export FPS", min_value=15, max_value=60, value=24)
resolution_w = st.sidebar.number_input("Width", min_value=240, max_value=3840, value=1280)
resolution_h = st.sidebar.number_input("Height", min_value=240, max_value=2160, value=720)

st.sidebar.subheader("Export final video")
output_name = st.sidebar.text_input("Output filename", value="final_video.mp4")
if st.sidebar.button("Render & Export"):
    if not st.session_state.timeline:
        st.sidebar.warning("Timeline is empty")
    else:
        with st.spinner("Rendering — this may take a while..."):
            clips = []
            try:
                for item in st.session_state.timeline:
                    if item['type'] == 'video':
                        clip = VideoFileClip(item['path'])
                        s = float(item.get('start', 0) or 0)
                        e = item.get('end', None)
                        if e:
                            clip = clip.subclip(s, float(e))
                        else:
                            if s>0:
                                clip = clip.subclip(s)
                        # resize to target resolution width while keeping aspect ratio
                        clip = clip.resize(width=resolution_w)
                        clips.append(clip)
                    else:
                        img = Image.open(item['path']).convert('RGB')
                        # create ImageClip with duration
                        dur = float(item.get('duration', 3))
                        ic = ImageClip(item['path']).set_duration(dur)
                        ic = ic.resize(width=resolution_w)
                        clips.append(ic)

                final = concatenate_videoclips(clips, method="compose")
                final = final.set_fps(fps)
                out_path = os.path.join(tempfile.gettempdir(), output_name)
                # optional: set audio
                final.write_videofile(out_path, codec='libx264', audio_codec='aac')
                st.success("Export complete")
                st.video(out_path)
                # create download button
                with open(out_path, 'rb') as f:
                    st.download_button('Download video', f, file_name=output_name, mime='video/mp4')
            except Exception as e:
                st.error(f"Rendering failed: {e}")

st.sidebar.markdown('---')
st.sidebar.markdown('Tips:')
st.sidebar.markdown('- Install ffmpeg on your machine; MoviePy needs it.')
st.sidebar.markdown('- Provide a PEXELS_API_KEY in Streamlit secrets or environment variables for online search.')

# Footer
st.markdown("---")
st.caption("Built with Streamlit + MoviePy — simple editor for assembling clips and images")
