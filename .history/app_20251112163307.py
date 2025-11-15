from datetime import date
from typing import Optional, Dict, Any, List

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
    st.title("Welcome to the Music Therapy Platform")
    st.caption("Log in or sign up to manage therapy sessions for your clients.")

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
            cols = st.columns([3, 1])
            with cols[0]:
                st.subheader(profile["child_name"])
                if profile.get("dob"):
                    st.caption(f"Date of Birth: {profile['dob']}")
                st.caption(f"Default Target Mood: {profile.get('default_target_mood', 'calm').title()}")

                if st.session_state["user_role"] == "therapist":
                    parents = database.get_parents_for_profile(profile["id"])
                    if parents:
                        st.markdown(
                            "**Connected Parents:** " + ", ".join(p.get("name") or p["email"] for p in parents)
                        )
                    invites = database.list_invites_for_profile(profile["id"])
                    pending = [invite for invite in invites if invite["status"] == "pending"]
                    if pending:
                        with st.expander("Pending Invitations"):
                            for invite in pending:
                                st.write(f"{invite['email']} — code: `{invite['token']}`")
            with cols[1]:
                if st.button("Open Profile", key=f"select_profile_{profile['id']}"):
                    set_active_profile(profile)
                    trigger_rerun()

        if st.session_state["user_role"] == "therapist":
            with st.expander(f"Invite a Parent/Guardian for {profile['child_name']}"):
                with st.form(f"invite_form_{profile['id']}"):
                    email = st.text_input(
                        "Parent Email",
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

            webrtc_ctx = webrtc_streamer(key="webcam", video_processor_factory=VideoProcessor)

            last = None
            if webrtc_ctx and webrtc_ctx.video_processor:
                last = getattr(webrtc_ctx.video_processor, "last_emotion", None)
            st.write(f"Detected: {last or 'None'}")

            if st.button("Lock in Mood and Get Recommendation"):
                st.session_state["detected_mood"] = last

    detected = st.session_state.get("detected_mood")
    if detected:
        target_mood = profile.get("default_target_mood") or "calm"
        st.header(f"Detected Mood: {detected}")
        st.caption(f"Guiding session toward: **{target_mood.title()}**")
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
    st.title(f"Progress Dashboard — {profile['child_name']}")

    history_df = database.get_history(profile["id"])
    if history_df.empty:
        st.info("No session history yet.")
        return

    st.subheader("Mood Over Time")
    mood_order = {"sad": -1, "neutral": 0, "happy": 1}
    mood_series = history_df["start_mood"].map(mood_order).fillna(0)
    mood_series.index = pd.to_datetime(history_df["timestamp"])  # type: ignore
    st.line_chart(mood_series)

    st.subheader("Session Feedback Summary")
    st.bar_chart(history_df["feedback_emoji"].value_counts())

    st.subheader("Full Session History")
    st.dataframe(history_df)


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
        st.caption(f"Logged in as {display_name} ({role.title()})")
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
    if not require_authentication():
        render_login_signup()
    else:
        render_authenticated_app()


if __name__ == "__main__":
    main()
