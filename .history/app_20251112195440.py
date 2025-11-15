from datetime import date
from typing import Optional, Dict, Any, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
import streamlit as st

import database
from music_engine import MusicEngine
from recommendation_logic import generate_playlist

# Optional imports for webcam mode
webrtc_streamer = None
av = None
cv2 = None
analyze_frame = None

_dependency_errors: List[Tuple[str, str]] = []

try:
    from streamlit_webrtc import webrtc_streamer as _webrtc_streamer

    webrtc_streamer = _webrtc_streamer
except ImportError as exc:
    _dependency_errors.append(("streamlit-webrtc", str(exc)))

try:
    import av as _av  # type: ignore[assignment]

    av = _av
except ImportError as exc:
    _dependency_errors.append(("av", str(exc)))

try:
    import cv2 as _cv2  # type: ignore[assignment]

    cv2 = _cv2
except ImportError as exc:
    _dependency_errors.append(("opencv-python-headless", str(exc)))

try:
    from emotion_detector import analyze_frame as _analyze_frame

    analyze_frame = _analyze_frame
except Exception as exc:  # noqa: BLE001 - expose exact failure to the UI
    _dependency_errors.append(("emotion_detector", str(exc)))


st.set_page_config(page_title="Music Therapy Recommender", layout="wide")

database.init_db()
engine = MusicEngine()

TARGET_MOODS: List[str] = getattr(
    database,
    "TARGET_MOODS",
    ["calm", "happy", "focused", "energized", "relaxed"],
)

MOOD_OPTIONS = ["happy", "sad", "angry", "fear", "surprise", "disgust", "neutral"]

THEMES: Dict[str, Dict[str, str]] = {
    "light": {
        "label": "Light",
        "primary": "#3A86FF",
        "primary_accent": "#2651B5",
        "background": "linear-gradient(135deg, #f7f8ff 0%, #eef5ff 100%)",
        "surface": "rgba(255, 255, 255, 0.94)",
        "surface_alt": "rgba(247, 249, 255, 0.95)",
        "text": "#1F2933",
        "muted": "#4A5568",
        "border": "rgba(58, 134, 255, 0.14)",
        "shadow": "0 18px 40px rgba(58, 134, 255, 0.08)",
        "input_bg": "rgba(255, 255, 255, 0.98)",
        "input_border": "rgba(58, 134, 255, 0.18)",
        "input_text": "#1F2933",
    },
    "dark": {
        "label": "Midnight",
        "primary": "#7FDBDA",
        "primary_accent": "#49B9B0",
        "background": "radial-gradient(circle at top, #101422 0%, #05070F 60%)",
        "surface": "rgba(15, 19, 30, 0.9)",
        "surface_alt": "rgba(24, 30, 45, 0.92)",
        "text": "#E5ECFF",
        "muted": "#94A3B8",
        "border": "rgba(127, 219, 218, 0.12)",
        "shadow": "0 18px 40px rgba(8, 12, 22, 0.5)",
        "input_bg": "rgba(18, 23, 33, 0.9)",
        "input_border": "rgba(127, 219, 218, 0.2)",
        "input_text": "#E5ECFF",
    },
}


def _text_color_css(theme_key: str) -> str:
    color = "#000000" if theme_key == "light" else "var(--app-text)"
    selectors = [
        ".stMarkdown p",
        ".stMarkdown div",
        ".stMarkdown span",
        ".stMarkdown li",
        ".stTabs",
        "label",
        ".stRadio > label",
        ".stCheckbox > label",
        ".stTextInput label",
        ".stSelectbox label",
        ".stDateInput label",
        ".stMetric",
        ".stDataFrame div",
        ".stCaption",
        ".st-dataframe",
        '.stSelectbox div[data-baseweb="select"] span',
    ]
    selector_block = ",\n    ".join(selectors)
    return (
        f"{selector_block} {{\n"
        f"        color: {color};\n"
        "    }\n"
    )


def apply_theme(theme_key: str) -> None:
    theme = THEMES.get(theme_key, THEMES["dark"])
    st.session_state["theme"] = theme_key
    text_css = _text_color_css(theme_key)

    css = f"""
    <style>
    :root {{
        --app-primary: {theme['primary']};
        --app-primary-accent: {theme['primary_accent']};
        --app-text: {theme['text']};
        --app-muted: {theme['muted']};
        --app-surface: {theme['surface']};
        --app-surface-alt: {theme['surface_alt']};
        --app-border: {theme['border']};
        --app-shadow: {theme['shadow']};
        --app-input-bg: {theme['input_bg']};
        --app-input-border: {theme['input_border']};
        --app-input-text: {theme['input_text']};
    }}

    .stApp {{
        background: {theme['background']};
        color: var(--app-text);
    }}

    .stAppViewContainer {{
        padding: 0 !important;
    }}

    .block-container {{
        padding: 2.2rem 2.5rem 3.2rem 2.5rem;
        border-radius: 1.4rem;
        background: var(--app-surface);
        box-shadow: var(--app-shadow);
        backdrop-filter: blur(18px);
    }}

    h1, h2, h3, h4 {{
        color: var(--app-text);
        letter-spacing: -0.02em;
    }}

    .app-hero {{
        padding: 1.8rem 2.4rem;
        border-radius: 1.2rem;
        background: var(--app-surface-alt);
        border: 1px solid var(--app-border);
        box-shadow: 0 12px 30px rgba(0,0,0,0.25);
        color: var(--app-text);
    }}

    .app-hero h1 {{
        font-size: 2.3rem;
        margin-bottom: 0.2rem;
    }}

    .tagline {{
        color: var(--app-muted);
        font-size: 1.05rem;
        margin-bottom: 0.2rem;
    }}

    .badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.2rem 0.8rem;
        border-radius: 999px;
        background: rgba(127, 219, 218, 0.16);
        color: var(--app-primary);
        font-size: 0.85rem;
        font-weight: 600;
    }}

    .profile-shell {{
        border-radius: 1.2rem;
        padding: 1.6rem;
        border: 1px solid var(--app-border);
        background: var(--app-surface-alt);
        box-shadow: 0 16px 32px rgba(0,0,0,0.35);
        color: var(--app-text);
        margin-bottom: 1rem;
    }}

    .profile-shell .meta {{
        color: var(--app-muted);
        font-size: 0.95rem;
        margin-bottom: 0.6rem;
    }}

    .session-section {{
        background: var(--app-surface-alt);
        border-radius: 1.25rem;
        border: 1px solid var(--app-border);
        padding: 1.6rem 1.8rem;
        box-shadow: 0 18px 36px rgba(0,0,0,0.35);
        margin-top: 1.3rem;
    }}

    .insights-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
        gap: 1rem;
        margin: 1rem 0 1.5rem 0;
    }}

    .insight-card {{
        background: var(--app-surface-alt);
        border-radius: 1.1rem;
        border: 1px solid var(--app-border);
        padding: 1.1rem 1.2rem;
        box-shadow: 0 16px 30px rgba(0,0,0,0.28);
        color: var(--app-text);
    }}

    .insight-card h4 {{
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--app-muted);
        margin-bottom: 0.4rem;
    }}

    .insight-card .value {{
        font-size: 1.9rem;
        font-weight: 700;
        color: var(--app-primary);
    }}

    .insight-card .hint {{
        font-size: 0.85rem;
        color: var(--app-muted);
    }}

    .chart-frame {{
        background: var(--app-surface-alt);
        border-radius: 1.1rem;
        border: 1px solid var(--app-border);
        padding: 1.2rem 1.3rem 1rem 1.3rem;
        box-shadow: 0 18px 36px rgba(0,0,0,0.32);
        margin-bottom: 1.2rem;
    }}

    .chart-frame h4 {{
        margin-bottom: 0.45rem;
        font-size: 0.96rem;
        color: var(--app-muted);
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }}

    .insights-grid .hint {{
        color: var(--app-muted);
    }}

    .stDataFrame {{
        border-radius: 1rem;
        overflow: hidden;
        border: 1px solid var(--app-border);
        background: var(--app-surface-alt);
    }}

    div[data-testid="stButton"] button {{
        border-radius: 999px;
        padding: 0.5rem 1.7rem;
        border: 1px solid transparent;
        background: var(--app-primary);
        color: #ffffff;
        font-weight: 600;
        letter-spacing: 0.01em;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}

    div[data-testid="stButton"] button:hover {{
        background: var(--app-primary-accent);
        transform: translateY(-1px);
        box-shadow: 0 12px 25px rgba(127,219,218,0.25);
    }}

    {text_css}

    label, .stRadio > label, .stCheckbox > label, .stTextInput label, .stSelectbox label, .stDateInput label {{
        color: var(--app-muted);
        font-weight: 600;
    }}

    .stSelectbox div[data-baseweb="select"] > div {{
        background: var(--app-input-bg);
        border-radius: 0.9rem;
        border: 1px solid var(--app-input-border);
        color: var(--app-input-text);
    }}

    .stSelectbox div[data-baseweb="select"] span {{
        color: var(--app-input-text);
    }}

    .stDateInput input, .stTextInput input, .stPasswordInput input, .stTextArea textarea {{
        background: var(--app-input-bg) !important;
        color: var(--app-input-text) !important;
        border: 1px solid var(--app-input-border) !important;
        border-radius: 0.9rem !important;
        padding: 0.65rem 1rem !important;
        box-shadow: none !important;
    }}

    .stDateInput input:focus, .stTextInput input:focus, .stPasswordInput input:focus, .stTextArea textarea:focus {{
        border-color: var(--app-primary) !important;
        box-shadow: 0 0 0 3px rgba(127, 219, 218, 0.25) !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_theme_controls(container: "st.delta_generator.DeltaGenerator") -> None:  # type: ignore[name-defined]
    option_labels = {theme["label"]: key for key, theme in THEMES.items()}
    current_key = st.session_state.get("theme", "dark")
    current_label = next(label for label, key in option_labels.items() if key == current_key)
    selected_label = container.selectbox(
        "Interface Theme",
        options=list(option_labels.keys()),
        index=list(option_labels.keys()).index(current_label),
        key="theme_selectbox",
    )
    selected_key = option_labels[selected_label]
    if selected_key != current_key:
        st.session_state["theme"] = selected_key
        trigger_rerun()


def trigger_rerun() -> None:
    rerun_fn = getattr(st, "experimental_rerun", None) or getattr(st, "rerun", None)
    if rerun_fn:
        rerun_fn()  # type: ignore[operator]
    else:
        st.session_state["_needs_rerun_toggle"] = not st.session_state.get("_needs_rerun_toggle", False)


def ensure_session_defaults() -> None:
    defaults = {
        "mode": None,
        "detected_mood": None,
        "last_detected_emotion": None,
        "theme": "dark",
        "_needs_rerun_toggle": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def logout() -> None:
    for key in [
        "user_id",
        "user_role",
        "user_display_name",
        "selected_profile_id",
        "selected_profile_name",
        "selected_profile_target",
        "mode",
        "detected_mood",
        "last_detected_emotion",
        "current_playlist",
    ]:
        st.session_state.pop(key, None)


def require_authentication() -> bool:
    return "user_id" in st.session_state and "user_role" in st.session_state


def set_active_profile(profile: Dict[str, Any]) -> None:
    st.session_state["selected_profile_id"] = profile["id"]
    st.session_state["selected_profile_name"] = profile["child_name"]
    st.session_state["selected_profile_target"] = (
        profile.get("default_target_mood") or "calm"
    )
    st.session_state["mode"] = None
    st.session_state["detected_mood"] = None
    st.session_state["last_detected_emotion"] = None


def render_login_signup() -> None:
    with st.sidebar:
        st.markdown("### Personalize")
        render_theme_controls(st.sidebar)

    with st.container():
        st.markdown(
            """
            <div class="app-hero">
                <span class="badge">Therapists · Caregivers · Children</span>
                <h1>Music Therapy Studio</h1>
                <p class="tagline">
                    Coordinate evidence-based sessions, track emotional growth, and collaborate with families in one place.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        feature_cols = st.columns(3)
        feature_cols[0].markdown(
            "**🧭 Guided Sessions**  \nBlended webcam + manual mood detection to tailor playlists instantly."
        )
        feature_cols[1].markdown(
            "**🤝 Collaborative Care**  \nInvite caregivers securely and share progress in real time."
        )
        feature_cols[2].markdown(
            "**📈 Longitudinal Insight**  \nVisual dashboards surface mood trends and session outcomes."
        )

    tabs = st.tabs(["Log In", "Therapist Sign Up", "Parent Invitation"])

    with tabs[0]:
        with st.form("login_form"):
            role_label = st.radio("I am a", ["Therapist", "Parent"], horizontal=True)
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In")

            if submitted:
                if not email or not password:
                    st.error("Please provide both email and password.")
                else:
                    if role_label == "Therapist":
                        user = database.authenticate_therapist(email, password)
                        role = "therapist"
                    else:
                        user = database.authenticate_parent(email, password)
                        role = "parent"

                    if user:
                        st.session_state["user_id"] = user["id"]
                        st.session_state["user_role"] = role
                        st.session_state["user_display_name"] = user["name"]
                        st.success("Logged in successfully.")
                        trigger_rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")

    with tabs[1]:
        with st.form("therapist_signup_form"):
            st.subheader("Create a Therapist Account")
            name = st.text_input("Full Name")
            email = st.text_input("Professional Email")
            practice_name = st.text_input("Practice Name")
            license_number = st.text_input("License / Certification Number (optional)")
            password = st.text_input("Create Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Sign Up as Therapist")

            if submitted:
                if not all([name, email, password, confirm, practice_name]):
                    st.error("Please complete all required fields.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                else:
                    try:
                        therapist_id = database.create_therapist(
                            name=name,
                            email=email,
                            password=password,
                            practice_name=practice_name,
                            license_number=license_number or None,
                        )
                        st.session_state["user_id"] = therapist_id
                        st.session_state["user_role"] = "therapist"
                        st.session_state["user_display_name"] = name
                        st.success("Account created! Redirecting to your dashboard.")
                        trigger_rerun()
                    except ValueError as exc:
                        st.error(str(exc))

    with tabs[2]:
        st.subheader("Complete Your Parent Invitation")
        st.caption(
            "Use the invitation code you received via email from your therapist to create your account."
        )
        with st.form("parent_invite_form"):
            token = st.text_input("Invitation Code")
            name = st.text_input("Your Name")
            password = st.text_input("Create Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Activate Invitation")

            if submitted:
                if not all([token, name, password, confirm]):
                    st.error("Please complete all fields.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                else:
                    try:
                        parent = database.complete_parent_invite(token.strip(), name, password)
                        st.session_state["user_id"] = parent["id"]
                        st.session_state["user_role"] = "parent"
                        st.session_state["user_display_name"] = parent["name"]
                        st.success("Invitation accepted! Welcome aboard.")
                        trigger_rerun()
                    except ValueError as exc:
                        st.error(str(exc))


def render_child_selection() -> None:
    role = st.session_state["user_role"]
    user_id = st.session_state["user_id"]
    st.title("Select a Child Profile")

    if role == "therapist":
        st.caption("Create a child profile, then share the invite code with parents to collaborate.")
        profiles = database.get_profiles_for_therapist(user_id)
        with st.expander("Add New Child Profile", expanded=not profiles):
            with st.form("new_profile_form"):
                child_name = st.text_input("Child Name or Initials")
                default_dob = date(2015, 1, 1)
                dob_value = st.date_input(
                    "Date of Birth",
                    value=default_dob,
                    min_value=date(1990, 1, 1),
                    max_value=date.today(),
                    help="Use the actual date of birth when possible. An approximate date is acceptable.",
                )
                target_mood = st.selectbox(
                    "Default Target Mood",
                    TARGET_MOODS,
                    index=0,
                )
                guardian_email = st.text_input(
                    "Parent / Guardian Email (optional)",
                    help="Provide an email to generate an invite code automatically.",
                )
                submitted = st.form_submit_button("Create Child Profile")

                if submitted:
                    if not child_name:
                        st.error("Child name is required.")
                    else:
                        dob_str = dob_value.isoformat() if isinstance(dob_value, date) else None
                        try:
                            profile_id = database.create_profile(
                                child_name=child_name,
                                dob=dob_str,
                                default_target_mood=target_mood,
                                therapist_id=user_id,
                            )
                        except ValueError as exc:
                            st.error(str(exc))
                        else:
                            success_msg = f"Profile for {child_name} created."
                            if guardian_email:
                                token = database.create_parent_invite(profile_id, guardian_email)
                                success_msg += " Invitation code generated below."
                                st.success(success_msg)
                                st.code(token, language=None)
                                st.caption(
                                    "Share this code with the parent/guardian so they can complete their invitation."
                                )
                            else:
                                st.success(success_msg)
                            trigger_rerun()
    else:
        st.caption("Select one of your linked children to view their therapy tools.")
        profiles = database.get_profiles_for_parent(user_id)

    if not profiles:
        st.info(
            "No child profiles available yet. "
            + (
                "Create one using the form above."
                if role == "therapist"
                else "Contact your therapist if you were expecting an invitation."
            )
        )
        return

    st.subheader("Your Child Profiles")
    for profile in profiles:
        with st.container():
            st.markdown("---")
            st.markdown(
                f"""
                <div class="profile-shell">
                    <div class="badge">🎯 Default Target · {profile.get('default_target_mood', 'calm').title()}</div>
                    <h3>{profile['child_name']}</h3>
                    <p class="meta">
                        {(f"Date of Birth: {profile['dob']} · " if profile.get("dob") else "")}
                        Managed by therapist workspace
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            cols = st.columns([1, 1.3])
            with cols[0]:
                if st.button("Open Profile", key=f"select_profile_{profile['id']}"):
                    set_active_profile(profile)
                    trigger_rerun()
            if st.session_state["user_role"] == "therapist":
                with cols[1]:
                    parents = database.get_parents_for_profile(profile["id"])
                    if parents:
                        st.markdown(
                            "**Connected Parents:** " + ", ".join(p.get("name") or p["email"] for p in parents)
                        )
                    invites = database.list_invites_for_profile(profile["id"])
                    pending = [invite for invite in invites if invite["status"] == "pending"]
                    if pending:
                        st.markdown("_Pending invitations:_")
                        for invite in pending:
                            st.code(invite["token"], language=None)
                            st.caption(f"Shared with {invite['email']}")
                    with st.expander(f"Invite for {profile['child_name']}"):
                        with st.form(f"invite_form_{profile['id']}"):
                            email = st.text_input(
                                "Parent / Guardian Email",
                                key=f"invite_email_{profile['id']}",
                            )
                            submit_invite = st.form_submit_button("Generate Invitation Code")
                            if submit_invite:
                                if not email:
                                    st.error("Parent email is required to generate an invite.")
                                else:
                                    token = database.create_parent_invite(profile["id"], email)
                                    st.success("Invitation code created. Share it securely with the parent/guardian.")
                                    st.code(token, language=None)


def render_new_session(profile: Dict[str, Any]) -> None:
    st.title(f"New Session for {profile['child_name']}")
    st.caption(
        "Launch webcam mood detection or log the child's current state manually to curate a guided playlist."
    )

    if not engine.is_ready():
        st.warning(
            "MuSe dataset not found or invalid. Place 'muse_v3.csv' in the project root to enable recommendations."
        )
        return

    start_col, manual_col = st.columns(2)
    if start_col.button("Start with Webcam 📹"):
        st.session_state["mode"] = "webcam"
        st.session_state["detected_mood"] = None
        st.session_state["last_detected_emotion"] = None
    if manual_col.button("Start with Manual Input 👆"):
        st.session_state["mode"] = "manual"
        st.session_state["detected_mood"] = None
        st.session_state["last_detected_emotion"] = None

    mode = st.session_state.get("mode")

    if mode == "manual":
        st.subheader("Manual Mood Input")
        manual_mood = st.selectbox(
            "What is the child's current mood?",
            options=MOOD_OPTIONS,
            key="manual_mood",
        )
        if st.button("Get Recommendation", key="manual_get_recommendation"):
            st.session_state["detected_mood"] = manual_mood
    elif mode == "webcam":
        st.subheader("Webcam Mood Detection")
        if webrtc_streamer is None or analyze_frame is None or av is None or cv2 is None:
            st.error("Webcam dependencies not available. Install streamlit-webrtc, av, and opencv.")
        else:
            def video_frame_callback(frame: "av.VideoFrame") -> "av.VideoFrame":  # type: ignore[name-defined]
                av_frame = frame.to_ndarray(format="bgr24")
                emotion = analyze_frame(av_frame)
                if emotion:
                    st.session_state["last_detected_emotion"] = emotion
                    cv2.putText(
                        av_frame,
                        f"{emotion}",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA,
                    )
                return av.VideoFrame.from_ndarray(av_frame, format="bgr24")

            webrtc_streamer(
                key="webcam",
                video_frame_callback=video_frame_callback,
                media_stream_constraints={"video": True, "audio": False},
            )

            last = st.session_state.get("last_detected_emotion")
            st.write(f"Detected: {last or 'None'}")

            if st.button("Lock in Mood and Get Recommendation", key="webcam_lock"):
                st.session_state["detected_mood"] = last

    detected = st.session_state.get("detected_mood")
    if detected:
        target_mood = profile.get("default_target_mood") or "calm"
        st.markdown(
            f"""
            <div class="session-section">
                <h3>Detected Mood · {detected.title()}</h3>
                <p class="subtitle">We will gently guide toward <strong>{target_mood.title()}</strong> across the next sequence.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        playlist_df = generate_playlist(
            music_engine=engine,
            start_emotion=detected,
            target_emotion=target_mood,
            num_steps=5,
            tolerance=0.1,
        )

        if playlist_df.empty:
            st.info("No suitable songs found for the current plan. Try again or widen tolerance.")
        else:
            st.session_state["current_playlist"] = playlist_df
            st.subheader("Curated Playlist")
            for _, row in playlist_df.iterrows():
                track = row.get("track", "Unknown Track")
                artist = row.get("artist", "Unknown Artist")
                spotify_id = row.get("spotify_id")
                st.write(f"{track} by {artist}")
                if spotify_id:
                    embed_url = f"https://open.spotify.com/embed/track/{spotify_id}"
                    iframe = (
                        f'<iframe src="{embed_url}" width="100%" height="80" frameborder="0" '
                        f'allowtransparency="true" allow="encrypted-media"></iframe>'
                    )
                    st.markdown(iframe, unsafe_allow_html=True)

            st.subheader("How did this session go?")
            c1, c2, c3 = st.columns(3)
            feedback = None
            if c1.button("😞 Not Effective"):
                feedback = "sad"
            if c2.button("😐 Neutral"):
                feedback = "neutral"
            if c3.button("😊 Great"):
                feedback = "happy"

            if feedback is not None:
                playlist_json = st.session_state["current_playlist"].to_json()
                database.save_session(
                    profile_id=profile["id"],
                    start_mood=detected,
                    target_mood=target_mood,
                    feedback_emoji=feedback,
                    playlist_json=playlist_json,
                )
                st.success("Feedback saved! Session complete.")
                st.session_state["detected_mood"] = None
                st.session_state["mode"] = None
                st.session_state["last_detected_emotion"] = None
                st.session_state.pop("current_playlist", None)


def render_progress_dashboard(profile: Dict[str, Any]) -> None:
    st.title(f"Progress Dashboard — {profile['child_name']}")

    history_df = database.get_history(profile["id"])
    if history_df.empty:
        st.info("No session history yet.")
        return

    history_df = history_df.copy()
    history_df["timestamp"] = pd.to_datetime(history_df["timestamp"])
    history_df.sort_values("timestamp", inplace=True)

    total_sessions = len(history_df)
    last_session = history_df["timestamp"].max()
    positive_feedback = history_df["feedback_emoji"].str.lower().eq("happy").sum()
    positive_pct = int(round((positive_feedback / total_sessions) * 100)) if total_sessions else 0
    target_mode = history_df["target_mood"].dropna()
    top_target = target_mode.mode().iat[0].title() if not target_mode.empty else "Calm"

    insights_html = f"""
    <div class="insights-grid">
        <div class="insight-card">
            <h4>Total Sessions</h4>
            <div class="value">{total_sessions}</div>
            <p class="hint">Since onboarding</p>
        </div>
        <div class="insight-card">
            <h4>Positive Reflections</h4>
            <div class="value">{positive_pct}%</div>
            <p class="hint">Reported as “Great”</p>
        </div>
        <div class="insight-card">
            <h4>Last Session</h4>
            <div class="value">{last_session.strftime('%b %d')}</div>
            <p class="hint">{last_session.strftime('%Y')}</p>
        </div>
        <div class="insight-card">
            <h4>Preferred Target</h4>
            <div class="value">{top_target}</div>
            <p class="hint">Most frequently selected</p>
        </div>
    </div>
    """
    st.markdown(insights_html, unsafe_allow_html=True)

    mood_map = {
        "angry": -2.0,
        "fear": -1.4,
        "sad": -1.0,
        "disgust": -1.2,
        "neutral": 0.0,
        "surprise": 0.6,
        "happy": 1.0,
    }
    mood_numeric = history_df["start_mood"].map(mood_map).fillna(0)

    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.markdown('<div class="chart-frame"><h4>Mood Trajectory</h4>', unsafe_allow_html=True)
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(history_df["timestamp"], mood_numeric, color="#3a60e6", linewidth=2.3, marker="o")
        ax.fill_between(history_df["timestamp"], mood_numeric, color="#3a60e6", alpha=0.12)
        ax.set_ylabel("Valence-Arousal blend")
        ax.set_ylim(-2.2, 1.4)
        ax.grid(axis="y", linestyle="--", alpha=0.25)
        ax.tick_params(axis="x", rotation=20, labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        st.pyplot(fig, transparent=True)
        plt.close(fig)
        st.markdown("</div>", unsafe_allow_html=True)

    with chart_cols[1]:
        st.markdown('<div class="chart-frame"><h4>Feedback Mix</h4>', unsafe_allow_html=True)
        feedback_counts = history_df["feedback_emoji"].value_counts()
        fig, ax = plt.subplots(figsize=(4, 3.2))
        if feedback_counts.empty:
            ax.axis("off")
            ax.text(0.5, 0.5, "No feedback yet", ha="center", va="center", fontsize=10)
        else:
            colors = ["#3a60e6", "#8fa5ff", "#d9e0ff"]
            wedges, texts, autotexts = ax.pie(
                feedback_counts,
                labels=[label.title() for label in feedback_counts.index],
                autopct="%1.0f%%",
                startangle=90,
                colors=colors[: len(feedback_counts)],
                wedgeprops={"linewidth": 1, "edgecolor": "white"},
                textprops={"fontsize": 9},
            )
            centre_circle = plt.Circle((0, 0), 0.55, fc="white")
            fig.gca().add_artist(centre_circle)
            for autotext in autotexts:
                autotext.set_color("#1f2933")
        ax.axis("equal")
        st.pyplot(fig, transparent=True)
        plt.close(fig)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="chart-frame"><h4>Weekly Cadence</h4>', unsafe_allow_html=True)
    weekly_sessions = history_df.set_index("timestamp").resample("W").size()
    fig, ax = plt.subplots(figsize=(10, 3.2))
    if weekly_sessions.empty:
        ax.axis("off")
        ax.text(0.5, 0.5, "Sessions will appear here once logged.", ha="center", va="center", fontsize=10)
    else:
        ax.bar(weekly_sessions.index, weekly_sessions.values, width=5, color="#6a85f7")
        ax.set_ylabel("Sessions per week")
        ax.tick_params(axis="x", rotation=20, labelsize=8)
        ax.grid(axis="y", linestyle="--", alpha=0.25)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    st.pyplot(fig, transparent=True)
    plt.close(fig)
    st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("Recent Sessions")
    display_df = history_df.copy()
    display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_about(profile: Optional[Dict[str, Any]]) -> None:
    st.title("About This Platform")
    st.markdown(
        """
        This app implements the Iso-Principle using Russell's Circumplex Model of Affect.
        It maps detected emotions into Valence–Arousal space and gently guides towards personalized target moods
        using songs selected from a static dataset (MuSe). Playback uses embeddable players via `spotify_id`.
        """
    )
    if profile:
        st.caption(f"Currently viewing profile: {profile['child_name']}")


def render_authenticated_app() -> None:
    ensure_session_defaults()

    role = st.session_state["user_role"]
    display_name = st.session_state.get("user_display_name", "")

    with st.sidebar:
        st.title("Music Therapy")
        render_theme_controls(st.sidebar)
        st.caption(f"Logged in as {display_name} ({role.title()})")
        if st.button("Log Out", key="logout_button"):
            logout()
            trigger_rerun()
            return

    profile_id = st.session_state.get("selected_profile_id")
    active_profile = database.get_profile(profile_id) if profile_id else None

    if profile_id and not active_profile:
        st.warning("The selected profile is no longer available.")
        st.session_state["selected_profile_id"] = None
        trigger_rerun()
        return

    if not active_profile:
        render_child_selection()
        return

    st.sidebar.subheader("Active Child")
    st.sidebar.write(active_profile["child_name"])
    if st.sidebar.button("Switch Child", key="switch_child_button"):
        st.session_state["selected_profile_id"] = None
        trigger_rerun()
        return

    nav = st.sidebar.radio(
        "Navigation",
        ["New Session", "Progress Dashboard", "About"],
        key="nav_selection",
    )

    if nav == "New Session":
        render_new_session(active_profile)
    elif nav == "Progress Dashboard":
        render_progress_dashboard(active_profile)
    else:
        render_about(active_profile)


def main() -> None:
    ensure_session_defaults()
    apply_theme(st.session_state.get("theme", "dark"))
    if not require_authentication():
        render_login_signup()
    else:
        render_authenticated_app()


if __name__ == "__main__":
    main()
