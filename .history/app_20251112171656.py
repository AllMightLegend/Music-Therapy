from datetime import date
from typing import Optional, Dict, Any, List

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

import database
from music_engine import MusicEngine
from recommendation_logic import generate_playlist

# Optional imports for webcam mode
try:
    from streamlit_webrtc import webrtc_streamer
    import av
    import cv2
    from emotion_detector import analyze_frame
except Exception:  # allow app to run without webcam stack
    webrtc_streamer = None
    av = None
    cv2 = None
    analyze_frame = None


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
        ".stSelectbox div[data-baseweb=\"select\"] span",
    ]
    selector_block = ",\n    ".join(selectors)
    return (
        f"{selector_block} {{\n"
        f"        color: {color};\n"
        "    }\n"
    )


def trigger_rerun() -> None:
    rerun_fn = getattr(st, "experimental_rerun", None) or getattr(st, "rerun", None)
    if rerun_fn:
        rerun_fn()  # type: ignore[operator]
    else:
        st.session_state["_needs_rerun_toggle"] = not st.session_state.get("_needs_rerun_toggle", False)


def apply_theme(theme_key: str) -> None:
    theme = THEMES.get(theme_key, THEMES["light"])
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
        box-shadow: 0 12px 30px rgba(0,0,0,0.05);
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

    .stTabs [data-baseweb="tab-list"] button {{
        font-size: 1rem;
        letter-spacing: 0.01em;
    }}

    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        background: rgba(58, 134, 255, 0.08);
        color: var(--app-primary);
    }}

    div[data-testid="stMetric"] {{
        background: var(--app-surface-alt);
        border-radius: 1rem;
        padding: 1.4rem 1.2rem;
        border: 1px solid var(--app-border);
        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02);
    }}

    div[data-testid="stMetric"] label {{
        color: var(--app-muted);
        font-weight: 600;
    }}

    div[data-testid="stMetric"] p {{
        color: var(--app-primary);
        font-size: 1.6rem;
    }}

    .profile-card {{
        border-radius: 1.2rem;
        padding: 1.6rem;
        border: 1px solid var(--app-border);
        background: var(--app-surface-alt);
        box-shadow: 0 10px 25px rgba(0,0,0,0.08);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
        color: var(--app-text);
    }}

    .profile-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 18px 36px rgba(0,0,0,0.12);
    }}

    .profile-card h3 {{
        margin-bottom: 0.4rem;
        font-size: 1.4rem;
    }}

    .profile-chip {{
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.2rem 0.8rem;
        border-radius: 999px;
        background: rgba(58,134,255,0.12);
        color: var(--app-primary);
        font-size: 0.85rem;
        font-weight: 600;
    }}

    .profile-meta {{
        color: var(--app-muted);
        font-size: 0.95rem;
        margin-bottom: 0.6rem;
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
        box-shadow: 0 12px 25px rgba(58,134,255,0.25);
    }}

    div[data-testid="stButton"] button:focus-visible {{
        outline: 2px solid var(--app-primary);
        outline-offset: 2px;
    }}

    {"".join([
        ".stMarkdown p, .stMarkdown div, .stMarkdown span, .stMarkdown li,",
        " .stTabs, label, .stRadio > label, .stCheckbox > label,",
        " .stTextInput label, .stSelectbox label, .stDateInput label,",
        " .stMetric, .stDataFrame div, .stCaption,",
        " .st-dataframe, .stSelectbox div[data-baseweb=\"select\"] span {",
        f" color: {('#000000' if theme_key == 'light' else 'var(--app-text)')};",
        " }"
    ])}

    label, .stRadio > label, .stCheckbox > label, .stTextInput label, .stSelectbox label, .stDateInput label {{
        color: var(--app-muted);
        font-weight: 600;
    }}

    .stRadio div[role="radiogroup"] label span {{
        color: var(--app-text);
    }}

    .stRadio div[role="radiogroup"] label span::before {{
        border-color: var(--app-primary);
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
        box-shadow: 0 0 0 3px rgba(58, 134, 255, 0.25) !important;
    }}

    .stTextInput svg, .stPasswordInput svg, .stSelectbox svg {{
        color: var(--app-muted);
    }}

    {text_css}
    .badge {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        background: rgba(58,134,255,0.12);
        color: var(--app-primary);
        font-size: 0.8rem;
        border: 1px solid var(--app-border);
    }}

    .dataframe tbody tr {{
        background: rgba(255,255,255,0.04);
    }}

    .insight-card {{
        background: var(--app-surface-alt);
        border: 1px solid var(--app-border);
        border-radius: 1.2rem;
        padding: 1.4rem 1.6rem;
        box-shadow: 0 16px 30px rgba(0,0,0,0.08);
        color: var(--app-text);
    }}

    .chart-title {{
        font-weight: 600;
        margin-bottom: 0.6rem;
        color: var(--app-muted);
        letter-spacing: 0.02em;
        text-transform: uppercase;
        font-size: 0.85rem;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_theme_controls(container: "st.delta_generator.DeltaGenerator") -> None:  # type: ignore[name-defined]
    option_labels = {theme["label"]: key for key, theme in THEMES.items()}
    current_key = st.session_state.get("theme", "light")
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


def ensure_session_defaults() -> None:
    defaults = {
        "mode": None,
        "detected_mood": None,
        "theme": "light",
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


def render_login_signup() -> None:
    with st.sidebar:
        st.markdown("### Personalize")
        render_theme_controls(st.sidebar)

    with st.container():
        st.markdown(
            """
            <div class="app-hero">
                <h1>Music Therapy Studio</h1>
                <p class="tagline">
                    Craft personalized journeys for every child with clinically informed playlists and collaborative tools.
                </p>
                <span class="badge">Therapists · Parents · Children</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        feature_cols = st.columns(3)
        feature_cols[0].markdown("**🧭 Guided Sessions**  \nBlended webcam + manual mood detection to tailor playlists instantly.")
        feature_cols[1].markdown("**🤝 Collaborative Care**  \nInvite caregivers securely and share progress in real time.")
        feature_cols[2].markdown("**📈 Longitudinal Insight**  \nVisual dashboards surface mood trends and session outcomes.")

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
            st.subheader("Create a Therapist Workspace")
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
    st.title("Client Portfolio")

    if role == "therapist":
        st.caption("Create child profiles, invite caregivers, and manage their therapeutic experiences.")
        profiles = database.get_profiles_for_therapist(user_id)
        detailed_profiles = []
        total_pending_invites = 0
        total_parents_linked = 0
        for profile in profiles:
            parents = database.get_parents_for_profile(profile["id"])
            invites = database.list_invites_for_profile(profile["id"])
            pending_invites = [invite for invite in invites if invite["status"] == "pending"]
            total_pending_invites += len(pending_invites)
            total_parents_linked += len(parents)
            detailed_profiles.append(
                {
                    **profile,
                    "parents": parents,
                    "invites": invites,
                    "pending_invites": pending_invites,
                }
            )

        if profiles:
            metrics = st.columns(3)
            metrics[0].metric("Active Child Profiles", len(profiles))
            metrics[1].metric("Connected Parents", total_parents_linked)
            metrics[2].metric("Pending Invitations", total_pending_invites)

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
        st.caption("Choose your child's profile to view guided sessions and progress insights.")
        profiles = database.get_profiles_for_parent(user_id)
        detailed_profiles = []
        for profile in profiles:
            detailed_profiles.append(
                {
                    **profile,
                    "parents": [],
                    "invites": [],
                    "pending_invites": [],
                }
            )

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
    for idx in range(0, len(detailed_profiles), 2):
        row_profiles = detailed_profiles[idx : idx + 2]
        cols = st.columns(len(row_profiles))
        for col, profile in zip(cols, row_profiles):
            with col:
                meta_lines = []
                if profile.get("dob"):
                    meta_lines.append(f"Date of Birth: {profile['dob']}")
                if st.session_state["user_role"] == "therapist":
                    meta_lines.append(f"Linked Parents: {len(profile['parents'])}")
                meta_html = "<br/>".join(meta_lines)
                st.markdown(
                    f"""
                    <div class="profile-card">
                        <div class="profile-chip">🎯 Target: {profile.get('default_target_mood', 'calm').title()}</div>
                        <h3>{profile['child_name']}</h3>
                        <p class="profile-meta">
                            {meta_html if meta_html else "Profile ready for first session."}
                        </p>
                        {f"<p><strong>Connected Parents:</strong> {', '.join(p.get('name') or p['email'] for p in profile['parents'])}</p>" if profile['parents'] else ""}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                action_cols = st.columns([1, 1])
                with action_cols[0]:
                    if st.button("Open Profile", key=f"select_profile_{profile['id']}"):
                        set_active_profile(profile)
                        trigger_rerun()
                if st.session_state["user_role"] == "therapist":
                    with action_cols[1]:
                        with st.expander("Invite Parent", expanded=False):
                            with st.form(f"invite_form_{profile['id']}"):
                                email = st.text_input(
                                    "Parent Email",
                                    key=f"invite_email_{profile['id']}",
                                )
                                submit_invite = st.form_submit_button("Generate Invite")
                                if submit_invite:
                                    if not email:
                                        st.error("Parent email is required to generate an invite.")
                                    else:
                                        token = database.create_parent_invite(profile["id"], email)
                                        st.success("Invitation code created. Share securely with the parent/guardian.")
                                        st.code(token, language=None)

                    if profile["pending_invites"]:
                        with st.expander("Pending Invitations", expanded=False):
                            for invite in profile["pending_invites"]:
                                st.write(f"{invite['email']} — code: `{invite['token']}`")


def render_new_session(profile: Dict[str, Any]) -> None:
    st.title(f"New Session · {profile['child_name']}")
    target_mood = profile.get("default_target_mood") or "calm"
    st.markdown(
        f"""
        <div class="profile-chip">Guiding toward {target_mood.title()}</div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "Use live mood detection or manual input to tailor a therapeutic playlist. "
        "Each session is logged automatically for progress tracking."
    )

    if not engine.is_ready():
        st.warning(
            "MuSe dataset not found or invalid. Place 'muse_v3.csv' in the project root to enable recommendations."
        )
        return

    start_col, manual_col = st.columns(2)
    if start_col.button("Start with Webcam 📹"):
            st.session_state["mode"] = "webcam"
    if manual_col.button("Start with Manual Input 👆"):
            st.session_state["mode"] = "manual"

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
                class VideoProcessor:
                    def __init__(self) -> None:
                        self.last_emotion: Optional[str] = None

                    def recv(self, frame: "av.VideoFrame") -> "av.VideoFrame":  # type: ignore[name-defined]
                        av_frame = frame.to_ndarray(format="bgr24")
                        emotion = analyze_frame(av_frame)
                        if emotion:
                            self.last_emotion = emotion
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

            webrtc_ctx = webrtc_streamer(
                key="webcam",
                video_processor_factory=VideoProcessor,
                media_stream_constraints={
                    "video": {
                        "width": {"ideal": 640},
                        "height": {"ideal": 360},
                        "frameRate": {"ideal": 15},
                    },
                    "audio": False,
                },
                video_html_attrs={
                    "style": (
                        "display: block; width: 100%; max-width: 520px; height: 260px; "
                        "border-radius: 18px; margin: 0 auto;"
                    ),
                    "playsinline": True,
                },
            )

                last = None
                if webrtc_ctx and webrtc_ctx.video_processor:
                    last = getattr(webrtc_ctx.video_processor, "last_emotion", None)
                st.write(f"Detected: {last or 'None'}")

                if st.button("Lock in Mood and Get Recommendation"):
                    st.session_state["detected_mood"] = last

        detected = st.session_state.get("detected_mood")
        if detected:
        st.markdown(
            f"""
            <div class="app-hero" style="margin-top: 1.5rem; margin-bottom: 1rem;">
                <h2>Detected Mood · {detected.title()}</h2>
                <p class="tagline">Curated pathway balancing arousal and valence toward {target_mood.title()}.</p>
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
            st.subheader("Recommended Playlist")
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
            st.markdown(
                "<p class='tagline'>Share a quick reflection to shape upcoming sessions.</p>",
                unsafe_allow_html=True,
            )
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
                st.session_state.pop("current_playlist", None)


def render_progress_dashboard(profile: Dict[str, Any]) -> None:
    st.title(f"Progress Dashboard · {profile['child_name']}")
    st.markdown(
        """
        <div class="app-hero" style="margin-bottom: 1.2rem;">
            <h2>Longitudinal Insights</h2>
            <p class="tagline">
                Track emotional baselines, session feedback, and playlist outcomes to fine-tune the therapy plan.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    history_df = database.get_history(profile["id"])
        if history_df.empty:
            st.info("No session history yet.")
        return

    history_df["timestamp"] = pd.to_datetime(history_df["timestamp"])
    history_df = history_df.sort_values("timestamp")

    total_sessions = len(history_df)
    sessions_this_month = history_df[
        history_df["timestamp"].dt.to_period("M") == pd.Timestamp.today().to_period("M")
    ]
    positive_feedback = history_df["feedback_emoji"].str.lower().eq("happy").sum()
    positive_pct = f"{(positive_feedback / total_sessions * 100):.0f}%" if total_sessions else "0%"

    metric_cols = st.columns(3)
    metric_cols[0].metric("Recorded Sessions", total_sessions)
    metric_cols[1].metric("Sessions This Month", len(sessions_this_month))
    metric_cols[2].metric("Positive Feedback", positive_pct)

    theme = THEMES.get(st.session_state.get("theme", "light"), THEMES["light"])
    accent_color = theme["primary"]
    accent_alt = theme["primary_accent"]
    text_color = theme["text"]

    mood_order = {"angry": -2, "sad": -1, "neutral": 0, "happy": 1, "surprise": 1.2, "fear": -1.2, "disgust": -1.5}
    mood_numeric = history_df["start_mood"].map(mood_order).fillna(0)

    trend_col, dist_col = st.columns([1.6, 1])

    with trend_col:
        st.markdown("<div class='chart-title'>Mood Trajectory</div>", unsafe_allow_html=True)
        fig, ax = plt.subplots(figsize=(8, 3))
        fig.patch.set_alpha(0)
        ax.plot(
            history_df["timestamp"],
            mood_numeric,
            color=accent_color,
            linewidth=2.4,
            marker="o",
            markerfacecolor="white",
            markeredgewidth=2,
            markeredgecolor=accent_color,
        )
        ax.fill_between(history_df["timestamp"], mood_numeric, 0, color=accent_color, alpha=0.12)
        ax.set_ylim(-2.2, 1.6)
        ax.set_yticks([-2, -1, 0, 1])
        ax.set_yticklabels(["Intense", "Low", "Neutral", "Elevated"], color=text_color, fontsize=9)
        ax.tick_params(axis="x", rotation=15, labelsize=8, colors=text_color)
        ax.grid(axis="y", linestyle="--", alpha=0.25)
        for spine in ["top", "right", "left", "bottom"]:
            ax.spines[spine].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig, transparent=True, use_container_width=True)
        plt.close(fig)

    with dist_col:
        st.markdown("<div class='chart-title'>Feedback Mix</div>", unsafe_allow_html=True)
        feedback_counts = history_df["feedback_emoji"].value_counts()
        if feedback_counts.empty:
            st.info("Feedback not recorded yet.")
        else:
            feedback_colors = [accent_color, accent_alt, "#E0E7FF"]
            fig, ax = plt.subplots(figsize=(4, 4))
            fig.patch.set_alpha(0)
            wedges, texts, autotexts = ax.pie(
                feedback_counts,
                labels=[label.title() for label in feedback_counts.index],
                autopct="%1.0f%%",
                startangle=90,
                colors=feedback_colors[: len(feedback_counts)],
                textprops={"color": text_color, "fontsize": 9},
                wedgeprops={"linewidth": 1, "edgecolor": "white"},
            )
            centre_color = "#ffffff" if st.session_state.get("theme", "light") == "light" else "#0f131e"
            centre_circle = plt.Circle((0, 0), 0.55, fc=centre_color, alpha=0.6)
            fig.gca().add_artist(centre_circle)
            for autotext in autotexts:
                autotext.set_color(text_color)
                autotext.set_fontsize(9)
            ax.axis("equal")
            plt.tight_layout()
            st.pyplot(fig, transparent=True)
            plt.close(fig)

    cadence_col, streak_col = st.columns([1.4, 0.6])

    with cadence_col:
        st.markdown("<div class='chart-title'>Weekly Session Cadence</div>", unsafe_allow_html=True)
        cadence_series = history_df.set_index("timestamp").resample("W").size()
        if cadence_series.empty:
            st.info("Sessions will appear here once logged.")
        else:
            fig, ax = plt.subplots(figsize=(8, 3))
            fig.patch.set_alpha(0)
            ax.bar(cadence_series.index, cadence_series.values, color=accent_alt, width=5)
            ax.set_ylabel("Sessions", color=text_color, fontsize=9)
            ax.tick_params(axis="x", rotation=15, labelsize=8, colors=text_color)
            ax.tick_params(axis="y", labelsize=8, colors=text_color)
            ax.grid(axis="y", linestyle="--", alpha=0.2)
            for spine in ["top", "right", "left", "bottom"]:
                ax.spines[spine].set_visible(False)
            plt.tight_layout()
            st.pyplot(fig, transparent=True, use_container_width=True)
            plt.close(fig)

    with streak_col:
        st.markdown("<div class='chart-title'>Highlights</div>", unsafe_allow_html=True)
        last_session = history_df["timestamp"].max()
        positive_series = history_df.sort_values("timestamp")["feedback_emoji"].str.lower().eq("happy")
        consecutive_positive = 0
        for value in positive_series[::-1]:
            if value:
                consecutive_positive += 1
            else:
                break
        top_target = history_df["target_mood"].dropna()
        top_target_display = top_target.mode().iat[0].title() if not top_target.empty else "Calm"
        st.markdown(
            f"""
            <div class="insight-card">
                <p><strong>Last Session:</strong><br/>{last_session.strftime("%b %d, %Y")}</p>
                <p><strong>Positive Streak:</strong><br/>{int(consecutive_positive)} session(s)</p>
                <p><strong>Top Target Mood:</strong><br/>{top_target_display}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div class='chart-title' style='margin-top:1.4rem;'>Session Log</div>", unsafe_allow_html=True)
    styled_history = history_df.copy()
    styled_history["timestamp"] = styled_history["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(
        styled_history,
        use_container_width=True,
        hide_index=True,
    )


def render_about(profile: Optional[Dict[str, Any]]) -> None:
    st.title("About This Platform")
    st.markdown(
        """
        <div class="app-hero" style="margin-bottom: 1.2rem;">
            <h2>Evidence-Based Soundscapes</h2>
            <p class="tagline">
                The experience is rooted in the Iso Principle and Russell’s Circumplex Model of Affect,
                guiding each session with science-backed transitions and collaborative oversight.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write(
        "- **Curated Catalog:** Recommendations leverage MuSe dataset embeddings to balance valence and arousal.\n"
        "- **Flexible Delivery:** Switch between therapist-led, caregiver-driven, or autonomous at-home sessions.\n"
        "- **Transparent Progress:** Unified dashboards ensure everyone sees the same momentum and outcomes."
    )
    if profile:
        st.caption(f"Currently viewing profile: {profile['child_name']}")


def render_authenticated_app() -> None:
    ensure_session_defaults()

    role = st.session_state["user_role"]
    display_name = st.session_state.get("user_display_name", "")

    with st.sidebar:
        st.title("Music Therapy")
        st.caption(f"Logged in as {display_name} ({role.title()})")
        render_theme_controls(st.sidebar)
        if st.button("Log Out", key="logout_button"):
            logout()
            trigger_rerun()

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
    apply_theme(st.session_state.get("theme", "light"))
    if not require_authentication():
        render_login_signup()
    else:
        render_authenticated_app()


if __name__ == "__main__":
    main()
