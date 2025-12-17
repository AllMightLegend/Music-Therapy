import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Set environment variables BEFORE any OpenCV imports to prevent libGL.so.1 errors
# This is critical for Streamlit Cloud deployment (headless Linux environment)
os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "0")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("OPENCV_VIDEOIO_PRIORITY_MSMF", "0")

from datetime import date
from typing import Optional, Dict, Any, List, Tuple
from queue import Queue, Empty, Full

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
except (ImportError, OSError) as exc:
    # OSError catches libGL.so.1 and other system library errors
    _dependency_errors.append(("opencv-python-headless", str(exc)))
    cv2 = None

try:
    from emotion_detector import analyze_frame as _analyze_frame

    analyze_frame = _analyze_frame
except (ImportError, OSError, Exception) as exc:  # noqa: BLE001 - expose exact failure to the UI
    # OSError catches libGL.so.1 and other system library errors
    # This is common on Streamlit Cloud where system libraries are limited
    _dependency_errors.append(("emotion_detector", str(exc)))
    analyze_frame = None


st.set_page_config(page_title="Music Therapy Recommender", layout="wide")

database.init_db()

# Cache the MusicEngine to prevent re-initialization on every rerun
@st.cache_resource
def get_music_engine():
    """Initialize and cache the MusicEngine singleton."""
    return MusicEngine()

engine = get_music_engine()

TARGET_MOODS: List[str] = getattr(
    database,
    "TARGET_MOODS",
    ["calm", "happy", "focused", "energized", "relaxed"],
)

MOOD_OPTIONS = ["happy", "sad", "angry", "fearful", "surprised", "loving", "energized", "anxious", "calm", "focused"]


def normalize_emotion(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = str(value).strip().lower()
    if normalized not in MOOD_OPTIONS:
        return "neutral"
    return normalized

THEMES: Dict[str, Dict[str, str]] = {
    "light": {
        "label": "Light",
        "primary": "#6366f1",  # Modern indigo - more sophisticated than pure blue
        "primary_accent": "#4f46e5",  # Deeper indigo for hover states
        "background": "linear-gradient(135deg, #ffffff 0%, #f8fafc 50%, #f1f5f9 100%)",  # Cleaner white-to-slate gradient
        "surface": "rgba(255, 255, 255, 0.98)",  # More opaque for better readability
        "surface_alt": "rgba(248, 250, 252, 0.98)",  # Subtle off-white
        "text": "#0f172a",  # Slate-900 for strong contrast
        "muted": "#64748b",  # Slate-500 for secondary text
        "border": "rgba(203, 213, 225, 0.6)",  # Slate-300 with transparency
        "shadow": "0 20px 50px rgba(15, 23, 42, 0.08), 0 8px 16px rgba(15, 23, 42, 0.04)",  # Layered shadows for depth
        "input_bg": "rgba(255, 255, 255, 1.0)",  # Pure white inputs
        "input_border": "rgba(203, 213, 225, 0.8)",  # Visible but not harsh
        "input_text": "#0f172a",
        "success": "#10b981",  # Emerald-500 for positive feedback
        "warning": "#f59e0b",  # Amber-500 for warnings
        "error": "#ef4444",  # Red-500 for errors
        "accent_gradient": "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",  # Indigo to purple
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
    # 1. Determine main text color
    color = "var(--app-text)"
    
    # 2. Enhanced Button CSS for Light Mode
    button_css = ""
    if theme_key == "light":
        button_css = """
        /* Modern Button Styling for Light Mode */
        div[data-testid="stButton"] button, 
        div[data-testid="stFormSubmitButton"] button {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
            border: none !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3) !important;
            transition: all 0.3s ease !important;
        }

        /* Button Text */
        div[data-testid="stButton"] button p,
        div[data-testid="stFormSubmitButton"] button p {
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }

        /* Hover Effects - Lift and glow */
        div[data-testid="stButton"] button:hover,
        div[data-testid="stFormSubmitButton"] button:hover {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
            box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4) !important;
            transform: translateY(-2px) !important;
        }
        
        /* Active/Pressed State */
        div[data-testid="stButton"] button:active,
        div[data-testid="stFormSubmitButton"] button:active {
            transform: translateY(0px) !important;
            box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3) !important;
        }
        
        /* Info/Success/Warning Boxes with subtle colors */
        .stAlert {
            border-radius: 12px !important;
            border-left: 4px solid !important;
            backdrop-filter: blur(10px) !important;
        }
        
        div[data-baseweb="notification"][data-testid="stNotificationContentInfo"] {
            background-color: rgba(219, 234, 254, 0.8) !important;
            border-left-color: #3b82f6 !important;
        }
        
        div[data-baseweb="notification"][data-testid="stNotificationContentSuccess"] {
            background-color: rgba(220, 252, 231, 0.8) !important;
            border-left-color: #10b981 !important;
        }
        
        div[data-baseweb="notification"][data-testid="stNotificationContentWarning"] {
            background-color: rgba(254, 243, 199, 0.8) !important;
            border-left-color: #f59e0b !important;
        }
        
        div[data-baseweb="notification"][data-testid="stNotificationContentError"] {
            background-color: rgba(254, 226, 226, 0.8) !important;
            border-left-color: #ef4444 !important;
        }
        """

    # 3. General Text Rules
    return f"""
    .stRadio label p, 
    .stRadio div[role='radiogroup'] p,
    .stTextInput label p, 
    .stSelectbox label p, 
    .stCheckbox label p, 
    .stTabs button p,
    .stMarkdown p,
    .stMarkdown li,
    h1, h2, h3, h4, h5, h6 {{
        color: {color} !important;
    }}
    
    {button_css}
    """

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
        padding: 3rem 2.5rem 3.2rem 2.5rem;
        margin-top: 2rem;
        border-radius: 20px;
        background: var(--app-surface);
        box-shadow: var(--app-shadow);
        backdrop-filter: blur(20px);
        border: 1px solid var(--app-border);
    }}

    h1, h2, h3, h4 {{
        color: var(--app-text);
        letter-spacing: -0.02em;
        font-weight: 700;
    }}
    
    h1 {{
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }}
    
    h2 {{
        font-size: 2rem;
    }}

    .app-hero {{
        padding: 2rem 2.5rem;
        border-radius: 16px;
        background: var(--app-surface-alt);
        border: 1px solid var(--app-border);
        box-shadow: var(--app-shadow);
        color: var(--app-text);
    }}

    .app-hero h1 {{
        font-size: 2.5rem;
        margin-bottom: 0.3rem;
        background: linear-gradient(135deg, var(--app-primary) 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}

    .tagline {{
        color: var(--app-muted);
        font-size: 1.1rem;
        margin-bottom: 0.3rem;
        line-height: 1.6;
    }}

    .badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.35rem 1rem;
        border-radius: 999px;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%);
        color: var(--app-primary);
        font-size: 0.85rem;
        font-weight: 600;
        border: 1px solid rgba(99, 102, 241, 0.2);
    }}

    .profile-shell {{
        border-radius: 16px;
        padding: 1.8rem;
        border: 1px solid var(--app-border);
        background: var(--app-surface-alt);
        box-shadow: var(--app-shadow);
        color: var(--app-text);
        margin-bottom: 1rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    
    .profile-shell:hover {{
        transform: translateY(-2px);
        box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12), 0 12px 24px rgba(15, 23, 42, 0.06);
    }}

    .profile-shell .meta {{
        color: var(--app-muted);
        font-size: 0.95rem;
        margin-bottom: 0.6rem;
    }}

    .session-section {{
        background: var(--app-surface-alt);
        border-radius: 16px;
        border: 1px solid var(--app-border);
        padding: 1.8rem 2rem;
        box-shadow: var(--app-shadow);
        margin-top: 1.5rem;
    }}

    .insights-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.2rem;
        margin: 1.2rem 0 1.8rem 0;
    }}

    .insight-card {{
        background: var(--app-surface-alt);
        border-radius: 14px;
        border: 1px solid var(--app-border);
        padding: 1.3rem 1.4rem;
        box-shadow: var(--app-shadow);
        color: var(--app-text);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    
    .insight-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 24px 60px rgba(15, 23, 42, 0.14), 0 12px 24px rgba(15, 23, 42, 0.07);
    }}

    .insight-card h4 {{
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--app-muted);
        margin-bottom: 0.5rem;
        font-weight: 700;
    }}

    .insight-card .value {{
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, var(--app-primary) 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0.3rem 0;
    }}

    .insight-card .hint {{
        font-size: 0.85rem;
        color: var(--app-muted);
        margin-top: 0.3rem;
    }}

    .chart-frame {{
        background: var(--app-surface-alt);
        border-radius: 14px;
        border: 1px solid var(--app-border);
        padding: 1.4rem 1.5rem 1.2rem 1.5rem;
        box-shadow: var(--app-shadow);
        margin-bottom: 1.4rem;
    }}

    .chart-frame h4 {{
        margin-bottom: 0.6rem;
        font-size: 1rem;
        color: var(--app-text);
        letter-spacing: 0.02em;
        font-weight: 700;
    }}

    .insights-grid .hint {{
        color: var(--app-muted);
    }}

    .stDataFrame {{
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--app-border);
        background: var(--app-surface-alt);
        box-shadow: var(--app-shadow);
    }}

    div[data-testid="stButton"] button {{
        border-radius: 12px;
        padding: 0.65rem 1.8rem;
        border: none;
        background: linear-gradient(135deg, var(--app-primary) 0%, #8b5cf6 100%);
        color: #ffffff;
        font-weight: 600;
        letter-spacing: 0.01em;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    }}

    div[data-testid="stButton"] button:hover {{
        background: linear-gradient(135deg, var(--app-primary-accent) 0%, #7c3aed 100%);
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4);
    }}

    {text_css}

    label, .stRadio > label, .stCheckbox > label, .stTextInput label, .stSelectbox label, .stDateInput label {{
        color: var(--app-text);
        font-weight: 600;
        font-size: 0.95rem;
    }}

    .stSelectbox div[data-baseweb="select"] > div {{
        background: var(--app-input-bg);
        border-radius: 10px;
        border: 2px solid var(--app-input-border);
        color: var(--app-input-text);
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
    }}
    
    .stSelectbox div[data-baseweb="select"] > div:hover {{
        border-color: var(--app-primary);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
    }}
    
    .stSelectbox div[data-baseweb="select"] > div:focus-within {{
        border-color: var(--app-primary);
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }}

    .stSelectbox div[data-baseweb="select"] span {{
        color: var(--app-input-text);
    }}
    
    /* Text Input Styling */
    .stTextInput input {{
        background: var(--app-input-bg);
        border-radius: 10px;
        border: 2px solid var(--app-input-border);
        color: var(--app-input-text);
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
        padding: 0.65rem 1rem;
    }}
    
    .stTextInput input:hover {{
        border-color: var(--app-primary);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
    }}
    
    .stTextInput input:focus {{
        border-color: var(--app-primary);
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        outline: none;
    }}
    
    /* Radio Buttons */
    .stRadio div[role="radiogroup"] {{
        gap: 0.8rem;
    }}
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {{
        background: var(--app-surface);
        border-right: 1px solid var(--app-border);
    }}
    
    section[data-testid="stSidebar"] .block-container {{
        background: transparent;
        box-shadow: none;
        border: none;
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
    rerun_fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun_fn:
        rerun_fn()  # type: ignore[operator]
    else:
        st.session_state["_needs_rerun_toggle"] = not st.session_state.get("_needs_rerun_toggle", False)


def ensure_session_defaults() -> None:
    defaults = {
        "mode": None,
        "detected_mood": None,
        "last_detected_emotion": None,
        "_last_detected_tick": 0,
        "_last_processed_tick": 0,
        "theme": "dark",
        "_needs_rerun_toggle": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    if "_emotion_queue" not in st.session_state:
        st.session_state["_emotion_queue"] = Queue(maxsize=8)


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


def validate_email(email: str) -> tuple[bool, str]:
    """
    Validate email format.
    Returns (is_valid, error_message).
    """
    import re
    email = email.strip()
    if not email:
        return False, "Email is required."
    # Stricter email regex: local@domain.extension
    # local part: alphanumeric, dots, hyphens, underscores (no @ allowed)
    # domain: alphanumeric and hyphens (no @ allowed)
    # TLD: 2+ letters
    pattern = r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Email format is invalid. Use example@domain.com."
    # Additional check: only one @ symbol allowed
    if email.count('@') != 1:
        return False, "Email format is invalid. Use example@domain.com."
    if len(email) > 255:
        return False, "Email is too long (max 255 characters)."
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (!@#$%^&*)
    Returns (is_valid, error_message).
    """
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit (0-9)."
    if not any(c in "!@#$%^&*" for c in password):
        return False, "Password must contain at least one special character (!@#$%^&*)."
    return True, ""


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
    # Clear journey tracking for fresh start
    st.session_state.pop("emotion_path", None)
    st.session_state.pop("current_playlist", None)
    st.session_state.pop("current_from", None)
    st.session_state.pop("current_to", None)
    st.session_state["current_transition_step"] = 0


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
                # Validate email format
                email_valid, email_msg = validate_email(email)
                if not email_valid:
                    st.error(email_msg)
                else:
                    # For login, password is just checked for presence (strict validation on signup)
                    if not password:
                        st.error("Password is required.")
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
                else:
                    # Validate email format
                    email_valid, email_msg = validate_email(email)
                    if not email_valid:
                        st.error(email_msg)
                    elif password != confirm:
                        st.error("Passwords do not match.")
                    else:
                        pwd_valid, pwd_msg = validate_password(password)
                        if not pwd_valid:
                            st.error(pwd_msg)
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
                    # Validate password strength
                    pwd_valid, pwd_msg = validate_password(password)
                    if not pwd_valid:
                        st.error(pwd_msg)
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
                                success_msg += " Invitation code generated."
                                
                                # Try to send email automatically
                                import email_service
                                # Get therapist name from session state
                                therapist_name = st.session_state.get("user_display_name", "Your Therapist")
                                
                                if email_service.is_email_configured():
                                    email_success, email_msg = email_service.send_invitation_email(
                                        parent_email=guardian_email,
                                        child_name=child_name,
                                        invitation_code=token,
                                        therapist_name=therapist_name
                                    )
                                    
                                    if email_success:
                                        st.success(success_msg + f" ✅ Email sent to {guardian_email}")
                                        st.info(
                                            f"📧 An invitation email has been sent to **{guardian_email}** with instructions.\n\n"
                                            f"The parent can use the invitation code to create their account."
                                        )
                                    else:
                                        st.warning(success_msg + f" ⚠️ Email could not be sent: {email_msg}")
                                        st.code(token, language=None)
                                        st.caption(
                                            "Email service unavailable. Please share this code manually with the parent/guardian."
                                        )
                                else:
                                    st.success(success_msg)
                                    st.code(token, language=None)
                                    st.caption(
                                        "📋 Share this code with the parent/guardian so they can complete their invitation.\n\n"
                                        "💡 **Tip**: Configure email settings to automatically send invitations."
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
            # Show change target mood selector if therapist
            if st.session_state["user_role"] == "therapist":
                current_target = profile.get('default_target_mood', 'calm')
                
                change_col1, change_col2 = st.columns([2, 1])
                with change_col1:
                    new_target = st.selectbox(
                        "Change Target Mood:",
                        TARGET_MOODS,
                        index=TARGET_MOODS.index(current_target) if current_target in TARGET_MOODS else 0,
                        key=f"target_mood_select_{profile['id']}"
                    )
                with change_col2:
                    st.write("")  # Spacer
                    st.write("")  # Spacer to align button
                    if st.button("💾 Update", key=f"update_target_{profile['id']}", type="primary"):
                        if new_target != current_target:
                            success = database.update_target_mood(profile['id'], new_target, user_id)
                            if success:
                                st.success(f"✅ Target mood changed to **{new_target.title()}**")
                                # Clear emotion path to force recalculation in next session
                                if st.session_state.get("active_profile_id") == profile['id']:
                                    for key in ["emotion_path", "current_playlist", "current_from", "current_to"]:
                                        st.session_state.pop(key, None)
                                st.rerun()
                            else:
                                st.error("Failed to update target mood.")
                        else:
                            st.info("Target mood is already set to this value.")
            
            cols = st.columns([1, 1, 1.3])
            with cols[0]:
                if st.button("Open Profile", key=f"select_profile_{profile['id']}"):
                    set_active_profile(profile)
                    trigger_rerun()
            
            if st.session_state["user_role"] == "therapist":
                with cols[1]:
                    if st.button("🗑️ Delete", key=f"delete_profile_{profile['id']}", type="secondary"):
                        # Store profile ID to confirm deletion
                        st.session_state[f"confirm_delete_{profile['id']}"] = True
                        st.rerun()
                
                # Show confirmation dialog if delete was clicked
                if st.session_state.get(f"confirm_delete_{profile['id']}", False):
                    st.warning(f"⚠️ **Are you sure you want to delete {profile['child_name']}'s profile?**")
                    st.caption("This will permanently delete all session history, invitations, and parent access.")
                    
                    confirm_cols = st.columns([1, 1, 2])
                    with confirm_cols[0]:
                        if st.button("✅ Yes, Delete", key=f"confirm_yes_{profile['id']}", type="primary"):
                            success = database.delete_profile(profile['id'], user_id)
                            if success:
                                st.success(f"Profile for {profile['child_name']} has been deleted.")
                                # Clear confirmation state
                                st.session_state.pop(f"confirm_delete_{profile['id']}", None)
                                # If this was the active profile, clear it
                                if st.session_state.get("active_profile_id") == profile['id']:
                                    st.session_state.pop("active_profile_id", None)
                                st.rerun()
                            else:
                                st.error("Failed to delete profile. You may not have permission.")
                    with confirm_cols[1]:
                        if st.button("❌ Cancel", key=f"confirm_no_{profile['id']}"):
                            st.session_state.pop(f"confirm_delete_{profile['id']}", None)
                            st.rerun()
                
                with cols[2]:
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
        "Detect the child's mood and receive a personalized therapeutic music playlist."
    )
    
    # Add helpful notice about detection methods
    with st.expander("ℹ️ About Mood Detection Methods", expanded=False):
        st.markdown("""
        **📸 Webcam (Snapshot Mode)** - *Recommended*
        - Take a single photo for emotion detection
        - Most reliable and stable
        - Works on all platforms including cloud deployments
        - No connection issues
        
        **🎥 Webcam (Real-time Video)**
        - Continuous emotion detection from live video
        - May experience STUN/connection issues on some networks
        - Higher bandwidth requirements
        - Best for local deployments
        - If you see connection errors, use Snapshot mode instead
        
        **✏️ Manual Input** - *Always Works*
        - Manually select the child's current mood
        - No camera or AI required
        - Same quality recommendations
        - Perfect backup option
        """)

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
        # Clear journey tracking for fresh start
        st.session_state.pop("emotion_path", None)
        st.session_state.pop("current_playlist", None)
        st.session_state.pop("current_from", None)
        st.session_state.pop("current_to", None)
        st.session_state["current_transition_step"] = 0
    if manual_col.button("Start with Manual Input 👆"):
        st.session_state["mode"] = "manual"
        st.session_state["detected_mood"] = None
        st.session_state["last_detected_emotion"] = None
        # Clear journey tracking for fresh start
        st.session_state.pop("emotion_path", None)
        st.session_state.pop("current_playlist", None)
        st.session_state.pop("current_from", None)
        st.session_state.pop("current_to", None)
        st.session_state["current_transition_step"] = 0

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
        
        # Add option to choose between real-time and snapshot mode
        detection_method = st.radio(
            "Choose detection method:",
            ["📸 Snapshot (Recommended - More Reliable)", "🎥 Real-time Video (May have connection issues)"],
            key="detection_method",
            help="Snapshot mode is more stable and works better on cloud deployments"
        )
        
        use_snapshot = "Snapshot" in detection_method
        
        realtime_available = webrtc_streamer is not None and av is not None
        detector_available = analyze_frame is not None

        if not use_snapshot and realtime_available and detector_available:
            emotion_queue = st.session_state.get("_emotion_queue")
            if not isinstance(emotion_queue, Queue):
                emotion_queue = Queue(maxsize=12)
                st.session_state["_emotion_queue"] = emotion_queue
            
            # Initialize emotion history for smoothing
            if "_emotion_history" not in st.session_state:
                st.session_state["_emotion_history"] = []
            
            # Use a module-level variable for throttling (callbacks can't use session state reliably)
            import time
            from collections import Counter
            _last_analysis = {"time": 0}
            
            def video_frame_callback(frame: "av.VideoFrame") -> "av.VideoFrame":  # type: ignore[name-defined]
                av_frame = frame.to_ndarray(format="bgr24")
                
                # Throttle emotion detection: analyze every 1 second for more responsive detection
                current_time = time.time()
                if current_time - _last_analysis["time"] >= 1.0:  # Analyze once per second
                    _last_analysis["time"] = current_time
                    emotion = analyze_frame(av_frame)
                    if emotion:
                        emotion = normalize_emotion(emotion)
                        if emotion:
                            print(f"[app.py] Adding to queue: {emotion}")
                            try:
                                emotion_queue.put_nowait(emotion)
                                print(f"[app.py] Queue size: {emotion_queue.qsize()}")
                            except Full:
                                # Remove oldest and add new
                                try:
                                    emotion_queue.get_nowait()
                                    emotion_queue.put_nowait(emotion)
                                    print(f"[app.py] Queue was full, replaced oldest")
                                except:
                                    pass
                            if cv2 is not None:
                                cv2.putText(
                                    av_frame,
                                    emotion.title(),
                                    (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    1.0,
                                    (0, 255, 0),
                                    2,
                                    cv2.LINE_AA,
                                )
                        else:
                            print(f"[app.py] normalize_emotion returned None for: {emotion}")
                    else:
                        print(f"[app.py] analyze_frame returned None")
                
                return av.VideoFrame.from_ndarray(av_frame, format="bgr24")

            st.warning(
                "⚠️ **Real-time video may have connection issues.** "
                "If you experience problems, switch to **Snapshot mode** above for better reliability."
            )
            st.info("💡 **Tip**: Emotion detection runs every second. Hold your expression for 2-3 seconds for best results.")
            
            try:
                # Configure RTC (WebRTC) with proper STUN/TURN servers for better connectivity
                from streamlit_webrtc import WebRtcMode, RTCConfiguration
                
                rtc_configuration = RTCConfiguration(
                    {"iceServers": [
                        {"urls": ["stun:stun.l.google.com:19302"]},
                        {"urls": ["stun:stun1.l.google.com:19302"]},
                        {"urls": ["stun:stun2.l.google.com:19302"]},
                        {"urls": ["stun:stun3.l.google.com:19302"]},
                        {"urls": ["stun:stun4.l.google.com:19302"]},
                    ]}
                )
                
                ctx = webrtc_streamer(
                    key="webcam",
                    mode=WebRtcMode.SENDRECV,
                    rtc_configuration=rtc_configuration,
                    video_frame_callback=video_frame_callback,
                    media_stream_constraints={
                        "video": {
                            "width": {"ideal": 640, "max": 1280},
                            "height": {"ideal": 480, "max": 720},
                            "frameRate": {"ideal": 10, "max": 15}  # Lower framerate for better stability
                        },
                        "audio": False
                    },
                    async_processing=True,  # Process frames asynchronously for better performance
                )
            except Exception as e:
                st.error(f"❌ WebRTC connection failed: {str(e)}")
                st.info("💡 Please use **Snapshot mode** (select it above) for a more reliable experience.")
                ctx = None
            if ctx and ctx.state.playing:
                # Collect all detected emotions from queue
                from collections import Counter
                emotions_batch = []
                while True:
                    try:
                        emotions_batch.append(emotion_queue.get_nowait())
                    except Empty:
                        break
                
                # Add to history and keep last 10 emotions
                if emotions_batch:
                    print(f"[app.py] Collected {len(emotions_batch)} emotions from queue: {emotions_batch}")
                    st.session_state["_emotion_history"].extend(emotions_batch)
                    st.session_state["_emotion_history"] = st.session_state["_emotion_history"][-10:]
                    print(f"[app.py] Emotion history: {st.session_state['_emotion_history']}")
                
                # Use majority voting from recent history for stability
                if len(st.session_state["_emotion_history"]) >= 2:
                    emotion_counts = Counter(st.session_state["_emotion_history"][-5:])  # Last 5 detections
                    most_common_emotion = emotion_counts.most_common(1)[0][0]
                    print(f"[app.py] Most common emotion: {most_common_emotion}")
                    
                    if st.session_state.get("last_detected_emotion") != most_common_emotion:
                        st.session_state["last_detected_emotion"] = most_common_emotion
                        print(f"[app.py] Updated last_detected_emotion to: {most_common_emotion}")
                        st.session_state["_last_detected_tick"] = (
                            st.session_state.get("_last_detected_tick", 0) + 1
                        )
                        try:
                            trigger_rerun()
                        except Exception:
                            pass
            elif not ctx or not ctx.state.playing:
                # When webcam stops, finalize emotion using history
                if st.session_state.get("_emotion_history"):
                    from collections import Counter
                    emotion_counts = Counter(st.session_state["_emotion_history"])
                    final_emotion = emotion_counts.most_common(1)[0][0]
                    if st.session_state.get("last_detected_emotion") != final_emotion:
                        st.session_state["last_detected_emotion"] = final_emotion
                        st.session_state["detected_mood"] = final_emotion
            if cv2 is None:
                st.info(
                    "OpenCV overlay support is unavailable; detections won't render on the video feed."
                )
        
        # Snapshot mode section (always available)
        if use_snapshot or not realtime_available or not detector_available:
            if not use_snapshot and _dependency_errors:
                with st.expander("Show webcam dependency diagnostics"):
                    for name, message in _dependency_errors:
                        st.markdown(f"- `{name}`: {message}")
                
                st.warning(
                    "⚠️ Real-time webcam streaming has connection issues. "
                    "Using **Snapshot mode** instead (more reliable)."
                )

            if not detector_available:
                st.error(
                    "⚠️ Emotion detection is currently unavailable. "
                    "This is common on Streamlit Cloud due to system library limitations. "
                    "Please use **Manual Input** mode instead, or try deploying to a platform with full system access."
                )
                st.info(
                    "💡 **Tip**: The manual mood input feature works perfectly and provides the same playlist recommendations!"
                )
            else:
                st.success("📸 **Snapshot Mode Active** - More stable than real-time video")
                st.info(
                    "**How it works:** Take a photo showing the child's expression. "
                    "The AI will analyze it and detect the emotion. Much more reliable than video streaming!"
                )

            snapshot = st.camera_input("📷 Capture a snapshot of the child's face", key="webcam_snapshot")
            
            # Process snapshot if available and not already processed
            if snapshot is not None and detector_available:
                # Create a unique key for this snapshot to detect new captures
                snapshot_id = st.session_state.get("_snapshot_id", 0)
                current_snapshot_key = f"snapshot_{id(snapshot)}"
                last_processed_key = st.session_state.get("_last_snapshot_key", None)
                
                # Only process if this is a new snapshot
                if current_snapshot_key != last_processed_key:
                    try:
                        image = Image.open(snapshot)
                        frame_rgb = np.array(image)
                        if frame_rgb.ndim == 2:  # grayscale fallback
                            frame_rgb = np.stack([frame_rgb] * 3, axis=-1)
                        # Convert RGB to BGR for OpenCV convention (analyze_frame expects BGR)
                        frame_bgr = frame_rgb[:, :, ::-1]
                        
                        with st.spinner("🔍 Analyzing emotion... (this may take a few seconds)"):
                            emotion = normalize_emotion(analyze_frame(frame_bgr))
                        
                        # Mark this snapshot as processed
                        st.session_state["_last_snapshot_key"] = current_snapshot_key
                        
                        if emotion:
                            st.session_state["last_detected_emotion"] = emotion
                            st.session_state["_last_detected_tick"] = (
                                st.session_state.get("_last_detected_tick", 0) + 1
                            )
                            st.success(f"✅ Detected: **{emotion.title()}**")
                        else:
                            st.warning("⚠️ Couldn't determine the mood from that snapshot. Try another capture.")
                    except Exception as exc:  # noqa: BLE001 - show friendly error
                        st.error(f"Snapshot processing failed: {exc}")

        # Display detected emotion prominently
        last = st.session_state.get("last_detected_emotion")
        if last:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.info(f"🎭 **Current Detected Mood**: {last.title()}")
            with col2:
                if st.button("Clear Detection", key="clear_detection"):
                    st.session_state["last_detected_emotion"] = None
                    st.session_state["_last_snapshot_key"] = None
                    st.session_state["_emotion_history"] = []
                    st.session_state["detected_mood"] = None
                    # Clear the queue as well (only if it exists)
                    emotion_queue = st.session_state.get("_emotion_queue")
                    if emotion_queue is not None and isinstance(emotion_queue, Queue):
                        while not emotion_queue.empty():
                            try:
                                emotion_queue.get_nowait()
                            except:
                                break
        else:
            st.info("📊 No emotion detected yet. Capture a snapshot to get started!")

        normalized_last = normalize_emotion(last)
        if normalized_last and normalized_last != last:
            # The emotion was normalized, display the normalized version
            st.session_state["last_detected_emotion"] = normalized_last

        # Automatically lock in the mood when detected
        if normalized_last and not st.session_state.get("detected_mood"):
            st.session_state["detected_mood"] = normalized_last
        
        lock_button_label = f"Use {normalized_last.title()} as Starting Mood" if normalized_last else "Waiting for Emotion Detection..."
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Detected Mood**: {normalized_last.title() if normalized_last else 'None'}")
        with col2:
            if st.button("Use This Mood", key="webcam_lock", disabled=not normalized_last):
                st.session_state["detected_mood"] = normalized_last
                # Clear old journey data to force recalculation with new mood
                st.session_state.pop("emotion_path", None)
                st.session_state.pop("current_playlist", None)
                st.session_state.pop("current_from", None)
                st.session_state.pop("current_to", None)
                st.session_state["current_transition_step"] = 0
                st.success(f"✅ Using {normalized_last.title()} as starting mood!")

    detected = st.session_state.get("detected_mood")
    if detected:
        target_mood = profile.get("default_target_mood") or "calm"
        
        # Check if detected mood is the same as target mood
        if detected.lower().strip() == target_mood.lower().strip():
            st.markdown(
                f"""
                <div class="session-section">
                    <h3>Detected Mood · {detected.title()}</h3>
                    <p class="subtitle">You are already at your target emotional state: <strong>{target_mood.title()}</strong></p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.success(f"🎉 Great news! You're already feeling {detected.title()}, which is your target mood. No transition needed!")
            st.info("💡 **Tip**: You can still enjoy music that matches your current mood, or you can change your target mood in the profile settings.")
            
            # Provide option to reset or change target
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Detect Again", key="detect_again_same_mood"):
                    st.session_state["detected_mood"] = None
                    st.session_state["last_detected_emotion"] = None
                    st.session_state["mode"] = None
                    # Clear journey tracking for fresh start
                    st.session_state.pop("emotion_path", None)
                    st.session_state.pop("current_playlist", None)
                    st.session_state.pop("current_from", None)
                    st.session_state.pop("current_to", None)
                    st.session_state["current_transition_step"] = 0
                    st.rerun()
            with col2:
                if st.button("⚙️ Change Target Mood", key="change_target_same_mood"):
                    st.session_state["mode"] = None
                    # Clear journey tracking for fresh start
                    st.session_state.pop("emotion_path", None)
                    st.session_state.pop("current_playlist", None)
                    st.session_state.pop("current_from", None)
                    st.session_state.pop("current_to", None)
                    st.session_state["current_transition_step"] = 0
                    st.rerun()
            return  # Exit early, no playlist generation
        
        st.markdown(
            f"""
            <div class="session-section">
                <h3>Detected Mood · {detected.title()}</h3>
                <p class="subtitle">We will gently guide toward <strong>{target_mood.title()}</strong> across the next sequence.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        # Show the emotion transition path (ISO Principle)
        # IMPORTANT: Only calculate path once at the start of the journey
        # Reuse stored path to maintain consistency through multi-step transitions
        from recommendation_logic import find_emotion_path
        
        if "emotion_path" not in st.session_state:
            # First time - calculate and store the full path
            emotion_path = find_emotion_path(detected, target_mood)
            st.session_state["emotion_path"] = emotion_path
            st.session_state["original_detected_mood"] = detected  # Store original mood
        else:
            # Use stored path for consistency
            emotion_path = st.session_state["emotion_path"]
        
        # Track current transition step (initialize if not exists)
        if "current_transition_step" not in st.session_state:
            st.session_state["current_transition_step"] = 0
        
        # Get current step index
        current_step = st.session_state.get("current_transition_step", 0)
        
        # Make sure step is valid (can't exceed number of transitions)
        max_step = len(emotion_path) - 2  # Max valid step for transitions
        if current_step > max_step:
            current_step = max_step
            st.session_state["current_transition_step"] = current_step
        if current_step < 0:
            current_step = 0
            st.session_state["current_transition_step"] = 0
        
        # Display complete therapeutic journey
        st.markdown("---")
        st.markdown("### 🧭 Therapeutic Journey Plan")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**Complete Path**: {' → '.join([e.title() for e in emotion_path])}")
        with col2:
            st.markdown(f"**Total Steps**: {len(emotion_path) - 1} transition(s)")
        
        # Current session focus based on transition step
        if len(emotion_path) >= 2:
            # Each step represents a transition from emotion[i] to emotion[i+1]
            current_from = emotion_path[current_step]
            current_to = emotion_path[current_step + 1]
            
            st.info(
                f"🎯 **Current Session Focus**: Transitioning from **{current_from.title()}** to **{current_to.title()}**\n\n"
                f"This playlist is specifically designed to help you move from your current **{current_from.title()}** state "
                f"toward a more **{current_to.title()}** emotional state."
            )
            
            # Show remaining steps if multi-step journey
            if len(emotion_path) > 2:
                # Show what's left AFTER current transition completes
                remaining_path = emotion_path[current_step + 1:]
                if len(remaining_path) > 1:  # More than just the target
                    st.warning(
                        f"📋 **Next Steps for Therapist**: After this session, continue the journey:\n\n"
                        f"**Remaining Path**: {' → '.join([e.title() for e in remaining_path])}\n\n"
                        f"**Recommendation**: In subsequent sessions, create playlists for each transition "
                        f"({len(remaining_path) - 1} more session(s) recommended to reach **{target_mood.title()}**)"
                    )
            else:
                st.success(
                    f"✅ **Single-Step Journey**: This session will complete the full transition to **{target_mood.title()}**"
                )
        
        st.markdown("---")
        
        # Check if playlist was regenerated (from negative/neutral feedback)
        if st.session_state.get("playlist_regenerated", False):
            regen_count = st.session_state.get("regeneration_count", 1)
            st.info(
                f"🔄 **Regenerated Playlist** (Attempt #{regen_count})\n\n"
                f"This is a new set of songs based on your feedback. Different musical approach, same therapeutic goal."
            )
            # Clear the flag after showing the message
            st.session_state["playlist_regenerated"] = False
        
        # Generate playlist for current transition step (only if not already in session)
        if "current_playlist" not in st.session_state:
            playlist_df = generate_playlist(
                music_engine=engine,
                start_emotion=current_from,
                target_emotion=current_to,
                num_steps=5,
                tolerance=0.1,
            )
            st.session_state["current_playlist"] = playlist_df
            st.session_state["emotion_path"] = emotion_path  # Store for feedback
            st.session_state["current_from"] = current_from  # Store current transition
            st.session_state["current_to"] = current_to
            # Initialize regeneration counter
            st.session_state["regeneration_count"] = 0
        else:
            # Retrieve stored transition emotions for feedback section
            current_from = st.session_state.get("current_from", current_from)
            current_to = st.session_state.get("current_to", current_to)
        
        playlist_df = st.session_state.get("current_playlist")

        if playlist_df.empty:
            st.info("No suitable songs found for the current plan. Try again or widen tolerance.")
        else:
            # Show progress in journey
            progress_text = ""
            if len(emotion_path) > 2:
                progress_text = f" (Step {current_step + 1} of {len(emotion_path) - 1})"
            
            st.subheader(f"🎵 Curated Playlist: {current_from.title()} → {current_to.title()}{progress_text}")
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
            st.caption("Your feedback helps us adjust the therapy progression")
            
            # Use dynamic keys that include the current step to prevent button state persistence
            current_step_for_key = st.session_state.get("current_transition_step", 0)
            regen_count = st.session_state.get("regeneration_count", 0)
            button_suffix = f"_step{current_step_for_key}_regen{regen_count}"
            
            c1, c2, c3 = st.columns(3)
            feedback = None
            if c1.button("😞 Not Effective", key=f"feedback_sad{button_suffix}", use_container_width=True):
                feedback = "sad"
            if c2.button("😐 Neutral", key=f"feedback_neutral{button_suffix}", use_container_width=True):
                feedback = "neutral"
            if c3.button("😊 Great", key=f"feedback_happy{button_suffix}", use_container_width=True):
                feedback = "happy"

            if feedback is not None:
                # Save session to database
                playlist_json = st.session_state["current_playlist"].to_json()
                database.save_session(
                    profile_id=profile["id"],
                    start_mood=current_from,
                    target_mood=current_to,
                    feedback_emoji=feedback,
                    playlist_json=playlist_json,
                )
                
                # Smart feedback handling based on ISO principle
                if feedback in ["sad", "neutral"]:
                    # Negative/neutral feedback: Regenerate playlist for same transition
                    st.warning(
                        f"📝 **Feedback recorded:** The transition from **{current_from.title()}** to **{current_to.title()}** "
                        f"needs adjustment. Let's try a different playlist for the same transition."
                    )
                    st.info(
                        "💡 **What's happening:** We'll generate a new set of songs for this same emotional transition. "
                        "The therapeutic goal remains the same, but with different music that might work better."
                    )
                    
                    # Regenerate playlist with different random state
                    import random
                    new_random_state = random.randint(1, 10000)
                    
                    # Store regeneration flag for UI message
                    st.session_state["playlist_regenerated"] = True
                    st.session_state["regeneration_count"] = st.session_state.get("regeneration_count", 0) + 1
                    
                    new_playlist = generate_playlist(
                        music_engine=engine,
                        start_emotion=current_from,
                        target_emotion=current_to,
                        num_steps=5,
                        tolerance=0.1,
                        random_state=new_random_state
                    )
                    
                    if not new_playlist.empty:
                        st.session_state["current_playlist"] = new_playlist
                        st.success(
                            f"✨ **New playlist generated!** (Attempt #{st.session_state['regeneration_count']})\n\n"
                            f"We've created a different set of songs for the transition from **{current_from.title()}** to **{current_to.title()}**."
                        )
                        # Rerun to display the new playlist
                        st.rerun()
                    else:
                        st.error("Could not generate alternative playlist. Please try manual input.")
                        # Reset for new session
                        st.session_state["detected_mood"] = None
                        st.session_state["mode"] = None
                        st.session_state["last_detected_emotion"] = None
                        st.session_state.pop("current_playlist", None)
                        st.session_state["regeneration_count"] = 0
                
                elif feedback == "happy":
                    # Positive feedback: Move to next transition
                    current_step = st.session_state.get("current_transition_step", 0)
                    next_step = current_step + 1
                    
                    # Check if there are more transitions
                    if next_step < len(emotion_path) - 1:
                        # Move to next transition
                        st.session_state["current_transition_step"] = next_step
                        next_from = emotion_path[next_step]
                        next_to = emotion_path[next_step + 1]
                        
                        st.success(
                            f"🎉 **Great progress!** You've successfully transitioned from **{current_from.title()}** to **{current_to.title()}**."
                        )
                        st.info(
                            f"🎯 **Moving to next step:** We're now shifting from **{next_from.title()}** to **{next_to.title()}**.\n\n"
                            f"**Progress:** Step {next_step + 1} of {len(emotion_path) - 1} in your journey to **{target_mood.title()}**"
                        )
                        
                        # Generate playlist for next transition
                        next_playlist = generate_playlist(
                            music_engine=engine,
                            start_emotion=next_from,
                            target_emotion=next_to,
                            num_steps=5,
                            tolerance=0.1,
                        )
                        
                        if not next_playlist.empty:
                            # Update session state for next transition
                            st.session_state["current_playlist"] = next_playlist
                            st.session_state["detected_mood"] = next_from  # Update current mood
                            st.session_state["current_from"] = next_from  # Store new transition
                            st.session_state["current_to"] = next_to
                            # Reset regeneration counter for new transition
                            st.session_state["regeneration_count"] = 0
                            st.session_state["playlist_regenerated"] = False
                            
                            st.success(
                                f"✅ **Playlist generated for next transition!**\n\n"
                                f"Moving from **{next_from.title()}** to **{next_to.title()}**"
                            )
                            # Rerun to display the new playlist with feedback buttons
                            st.rerun()
                        else:
                            st.error("Could not generate next playlist. Starting new session.")
                            # Reset everything
                            st.session_state["detected_mood"] = None
                            st.session_state["mode"] = None
                            st.session_state["last_detected_emotion"] = None
                            st.session_state.pop("current_playlist", None)
                            st.session_state.pop("current_from", None)
                            st.session_state.pop("current_to", None)
                            st.session_state.pop("emotion_path", None)
                            st.session_state["current_transition_step"] = 0
                            st.session_state["regeneration_count"] = 0
                    
                    else:
                        # Journey complete!
                        st.balloons()
                        st.success(
                            f"🎊 **Journey Complete!** You've successfully reached your target mood: **{target_mood.title()}**\n\n"
                            f"You've completed all {len(emotion_path) - 1} transition(s) in your therapeutic journey."
                        )
                        st.info(
                            "✨ **Well done!** You can now:\n"
                            "- Start a new session\n"
                            "- View your progress in the Dashboard\n"
                            "- Set a new target mood"
                        )
                        
                        # Reset for new session
                        st.session_state["detected_mood"] = None
                        st.session_state["mode"] = None
                        st.session_state["last_detected_emotion"] = None
                        st.session_state.pop("current_playlist", None)
                        st.session_state.pop("current_from", None)
                        st.session_state.pop("current_to", None)
                        st.session_state.pop("emotion_path", None)
                        st.session_state["current_transition_step"] = 0
                        st.session_state["regeneration_count"] = 0


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

    chart_cols = st.columns(2)
    
    # Determine theme for chart colors
    current_theme = st.session_state.get("theme", "dark")
    is_light_theme = current_theme == "light"
    
    # Theme-adaptive colors
    if is_light_theme:
        text_color = "#0f172a"
        grid_color = "#cbd5e1"
        spine_color = "#94a3b8"
        bg_color = (0.97, 0.98, 0.99, 0.5)  # RGBA tuple for light background
        empty_text_color = "#64748b"
    else:
        text_color = "white"
        grid_color = "white"
        spine_color = "white"
        bg_color = (0, 0, 0, 0)  # Transparent RGBA tuple
        empty_text_color = "white"
    
    # Success Rate Trend - Simple and clear for therapists
    with chart_cols[0]:
        st.markdown('<div class="chart-frame"><h4>Session Success Trend</h4>', unsafe_allow_html=True)
        # Calculate rolling success rate (positive feedback over last 5 sessions)
        history_df['is_positive'] = history_df["feedback_emoji"].str.lower().eq("happy").astype(int)
        history_df['rolling_success'] = history_df['is_positive'].rolling(window=min(5, len(history_df)), min_periods=1).mean() * 100
        
        fig, ax = plt.subplots(figsize=(6, 3.2), facecolor=bg_color)
        ax.set_facecolor(bg_color)
        
        # Plot line with gradient effect
        ax.plot(history_df["timestamp"], history_df['rolling_success'], 
                color="#10b981", linewidth=3, marker="o", markersize=6, 
                markerfacecolor="#10b981", markeredgecolor="white", markeredgewidth=2,
                label="Success Rate", zorder=3)
        ax.fill_between(history_df["timestamp"], history_df['rolling_success'], 
                        color="#10b981", alpha=0.15, zorder=2)
        
        # Target line
        ax.axhline(y=70, color='#f59e0b', linestyle='--', linewidth=2, 
                   alpha=0.7, label='Target: 70%', zorder=1)
        
        ax.set_ylabel("Success Rate (%)", color=text_color, fontsize=11, fontweight=600)
        ax.set_ylim(0, 105)
        ax.grid(axis="y", linestyle="--", alpha=0.15, color=grid_color, linewidth=1)
        ax.tick_params(axis="x", rotation=25, labelsize=9, colors=text_color)
        ax.tick_params(axis="y", labelsize=10, colors=text_color)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color(spine_color)
        ax.spines["bottom"].set_linewidth(1.5)
        ax.spines["left"].set_color(spine_color)
        ax.spines["left"].set_linewidth(1.5)
        
        legend = ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
        legend.get_frame().set_facecolor(bg_color if is_light_theme else 'gray')
        legend.get_frame().set_edgecolor(spine_color)
        
        plt.tight_layout()
        st.pyplot(fig, transparent=True)
        plt.close(fig)
        st.caption("📊 Rolling average of positive feedback (last 5 sessions)")
        st.markdown("</div>", unsafe_allow_html=True)

    # Feedback Mix Pie Chart
    with chart_cols[1]:
        st.markdown('<div class="chart-frame"><h4>Feedback Distribution</h4>', unsafe_allow_html=True)
        feedback_counts = history_df["feedback_emoji"].value_counts()
        fig, ax = plt.subplots(figsize=(4.5, 3.4), facecolor=bg_color)
        ax.set_facecolor(bg_color)
        
        if feedback_counts.empty:
            ax.axis("off")
            ax.text(0.5, 0.5, "No feedback yet", ha="center", va="center", 
                   fontsize=11, color=empty_text_color, fontweight=500)
        else:
            # Modern color palette
            colors = ["#10b981", "#f59e0b", "#ef4444"]  # Emerald, Amber, Red
            
            wedges, texts, autotexts = ax.pie(
                feedback_counts,
                labels=[label.title() for label in feedback_counts.index],
                autopct="%1.0f%%",
                startangle=90,
                colors=colors[: len(feedback_counts)],
                wedgeprops={"linewidth": 2, "edgecolor": "white"},
                textprops={"fontsize": 10, "color": text_color, "fontweight": 600},
                pctdistance=0.75
            )
            
            # Donut hole with gradient effect
            if is_light_theme:
                centre_circle = plt.Circle((0, 0), 0.65, fc="#f8fafc", ec="#e2e8f0", linewidth=2)
            else:
                centre_circle = plt.Circle((0, 0), 0.65, fc="#1e293b", ec="#334155", linewidth=2)
            fig.gca().add_artist(centre_circle)
            
            # Style percentage text
            for autotext in autotexts:
                autotext.set_color("white")
                autotext.set_fontweight(700)
                autotext.set_fontsize(10)
            
            # Style labels
            for text in texts:
                text.set_color(text_color)
                text.set_fontweight(600)
        
        ax.axis("equal")
        plt.tight_layout()
        st.pyplot(fig, transparent=True)
        plt.close(fig)
        st.caption("🎯 Overall session satisfaction ratings")
        st.markdown("</div>", unsafe_allow_html=True)

    # Common Emotional Journeys - Very helpful for therapists
    st.markdown('<div class="chart-frame"><h4>Most Common Emotional Journeys</h4>', unsafe_allow_html=True)
    
    if is_light_theme:
        st.markdown('<p style="color: #64748b; font-size: 14px; margin-bottom: 12px; font-weight: 500;">Understanding frequent transitions helps plan future sessions</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p style="color: #a0aec0; font-size: 14px; margin-bottom: 12px;">Understanding frequent transitions helps plan future sessions</p>', unsafe_allow_html=True)
    
    # Create journey combinations
    history_df['journey'] = history_df['start_mood'].str.title() + ' → ' + history_df['target_mood'].str.title()
    journey_counts = history_df['journey'].value_counts().head(6)
    
    if not journey_counts.empty:
        fig, ax = plt.subplots(figsize=(10, 4), facecolor=bg_color)
        ax.set_facecolor(bg_color)
        
        # Gradient colors for bars
        colors_gradient = plt.cm.viridis(np.linspace(0.3, 0.9, len(journey_counts)))
        if is_light_theme:
            colors_gradient = ["#6366f1", "#8b5cf6", "#a855f7", "#c026d3", "#d946ef", "#e879f9"][:len(journey_counts)]
        
        bars = ax.barh(journey_counts.index, journey_counts.values, 
                      color=colors_gradient, alpha=0.9, height=0.7)
        
        # Add gradient effect to bars
        for bar in bars:
            bar.set_edgecolor("white" if is_light_theme else "#1e293b")
            bar.set_linewidth(1.5)
        
        # Add count labels on bars with better styling
        for i, (bar, count) in enumerate(zip(bars, journey_counts.values)):
            ax.text(count + 0.15, i, f'{int(count)}x', 
                   va='center', color=text_color, fontsize=10, fontweight='bold')
        
        ax.set_xlabel("Number of Sessions", color=text_color, fontsize=11, fontweight=600)
        ax.tick_params(axis="y", labelsize=10, colors=text_color)
        ax.tick_params(axis="x", labelsize=10, colors=text_color)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color(spine_color)
        ax.spines["bottom"].set_linewidth(1.5)
        ax.spines["left"].set_color(spine_color)
        ax.spines["left"].set_linewidth(1.5)
        ax.grid(axis="x", linestyle="--", alpha=0.15, color=grid_color, linewidth=1)
        
        plt.tight_layout()
        st.pyplot(fig, transparent=True)
        plt.close(fig)
    else:
        st.info("Complete more sessions to see journey patterns")
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
