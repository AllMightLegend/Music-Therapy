"""
Motion-based behavior detector for autistic children's stimming behaviors.
Detects flapping, hand-flapping, and other repetitive movements.
Uses MediaPipe Pose for skeletal keypoint detection, with optical flow fallback.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Union

# Optional imports - don't fail if these are missing
cv2 = None
np = None
try:
    import cv2 as _cv2
    import numpy as _np
    cv2 = _cv2
    np = _np
except (ImportError, OSError) as e:
    print(f"[motion_detector] OpenCV/NumPy import failed (disabling optical flow): {e}")

try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False


@dataclass
class MotionAnalysis:
    """Analysis result for detected motion in a video clip."""
    label: str  # "normal" or "fight" (or "flapping" for stimming)
    confidence: float
    motion_intensity: float  # 0.0 to 1.0
    arm_movement_intensity: float  # 0.0 to 1.0
    repetition_score: float  # 0.0 to 1.0 - higher means more repetitive
    frames_analyzed: int


class OpticalFlowBehaviorDetector:
    """
    Detects behaviors using optical flow analysis.
    Fallback method when MediaPipe is unavailable.
    """

    def _extract_frames(
        self,
        video_path: Union[str, Path],
        max_frames: int = 120,
        analysis_seconds: int = 10,
    ) -> List[np.ndarray]:
        """Extract frames from video."""
        if cv2 is None:
            raise RuntimeError(
                "OpenCV (cv2) not available. Install with: pip install opencv-python"
            )
        
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        frames: List[np.ndarray] = []
        start_time = time.time()

        while len(frames) < max_frames:
            ok, frame = capture.read()
            if not ok:
                break

            # Resize for faster processing
            h, w = frame.shape[:2]
            if w > 480:
                scale = 480 / w
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

            # Convert to grayscale for optical flow
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frames.append(gray)

            if analysis_seconds and (time.time() - start_time) >= analysis_seconds:
                break

        capture.release()

        if not frames:
            raise RuntimeError(f"No frames decoded from: {video_path}")

        return frames

    def analyze_video(
        self,
        video_path: Union[str, Path],
        max_frames: int = 120,
        analysis_seconds: int = 10,
    ) -> MotionAnalysis:
        """Analyze video using optical flow."""
        frames = self._extract_frames(video_path, max_frames, analysis_seconds)

        if len(frames) < 2:
            return MotionAnalysis(
                label="normal",
                confidence=0.6,
                motion_intensity=0.0,
                arm_movement_intensity=0.0,
                repetition_score=0.0,
                frames_analyzed=len(frames),
            )

        # Calculate optical flow
        motion_magnitudes: List[float] = []

        prev_frame = frames[0].copy()
        for curr_frame in frames[1:]:
            curr_frame = curr_frame.copy()
            try:
                # Calculate dense optical flow
                # Using Farneback method with minimal parameters
                # Use correct Farneback signature: (prev, next, flow, pyr_scale, levels,
                # winsize, iterations, poly_n, poly_sigma, flags)
                flow = cv2.calcOpticalFlowFarneback(
                    prev_frame,
                    curr_frame,
                    None,
                    0.5,    # pyr_scale
                    3,      # levels
                    15,     # winsize
                    3,      # iterations
                    5,      # poly_n
                    1.2,    # poly_sigma
                    0       # flags
                )
                
                # Calculate motion magnitude
                mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                avg_magnitude = float(np.mean(mag))
                motion_magnitudes.append(avg_magnitude)
            except Exception as e:
                # If optical flow fails on a frame, skip it
                continue

            prev_frame = curr_frame

        if not motion_magnitudes:
            # No motion detected
            return MotionAnalysis(
                label="normal",
                confidence=0.6,
                motion_intensity=0.0,
                arm_movement_intensity=0.0,
                repetition_score=0.0,
                frames_analyzed=len(frames),
            )

        avg_motion = float(np.mean(motion_magnitudes))
        max_motion = float(np.max(motion_magnitudes))
        std_motion = float(np.std(motion_magnitudes))

        # Detect repetitive motion patterns using spectral analysis (FFT)
        repetition_score = 0.0
        if len(motion_magnitudes) > 6:
            mags = np.array(motion_magnitudes)
            mags_d = mags - np.mean(mags)
            try:
                fft = np.abs(np.fft.rfft(mags_d))
                if fft.sum() > 0:
                    # Ignore DC (index 0)
                    fft[0] = 0.0
                    peak = float(np.max(fft))
                    total = float(fft.sum())
                    repetition_score = float(peak / (total + 1e-9))
                    # Normalize to 0-1 and clamp
                    repetition_score = max(0.0, min(1.0, repetition_score))
            except Exception:
                # Fallback to simple time-domain heuristic
                diffs = np.abs(np.diff(motion_magnitudes))
                mean_diff = float(np.mean(diffs)) if len(diffs) else 0.0
                if mean_diff > 0.01:
                    repetition_score = float(1.0 - min(1.0, np.std(diffs) / (mean_diff + 1e-6)))
                repetition_score = max(0.0, min(1.0, repetition_score))
            # Time-domain peak counting to capture oscillatory flapping
            mean_val = float(np.mean(mags))
            std_val = float(np.std(mags))
            peak_thresh = mean_val + max(0.05, 0.3 * std_val)
            peaks = 0
            for i in range(1, len(mags) - 1):
                if mags[i] > mags[i - 1] and mags[i] > mags[i + 1] and mags[i] > peak_thresh:
                    peaks += 1
            # Estimate peaks per second from analysis_seconds (fallback if not provided)
            secs = analysis_seconds if analysis_seconds else max(1, len(mags) / 15.0)
            peaks_per_sec = peaks / secs
            # Convert to repetition_score (2-4 peaks/sec indicates flapping)
            peak_score = min(1.0, peaks_per_sec / 3.0)
            # Combine spectral and peak scores (weighted)
            repetition_score = max(repetition_score * 0.6, peak_score * 0.8)
            repetition_score = max(0.0, min(1.0, repetition_score))

        # Normalize motion intensity
        motion_intensity = min(1.0, avg_motion / 5.0) if avg_motion > 0 else 0.0

        # Classification logic
        # Slightly more permissive thresholds for flapping detection
        is_flapping = repetition_score > 0.25 and motion_intensity > 0.08
        is_intense = max_motion > 3.0 and motion_intensity > 0.3

        if is_flapping:
            # Optical flow detected repetitive motion — treat as flapping/stimming
            label = "flapping"
            confidence = min(0.95, 0.6 + repetition_score * 0.35)
        elif is_intense:
            label = "fight"
            confidence = min(0.95, 0.6 + motion_intensity * 0.35)
        else:
            label = "normal"
            confidence = min(0.95, 0.7 + (1.0 - motion_intensity) * 0.25)

        return MotionAnalysis(
            label=label,
            confidence=confidence,
            motion_intensity=motion_intensity,
            arm_movement_intensity=motion_intensity,  # Approximation
            repetition_score=repetition_score,
            frames_analyzed=len(frames),
        )


class MotionBehaviorDetector:
    """
    Detects behaviors based on motion analysis.
    - "normal": Calm, minimal movement
    - "fight": Aggressive, high-intensity movements
    - Detects stimming behaviors like flapping hands
    """

    def __init__(self):
        self.has_mediapipe = HAS_MEDIAPIPE
        if HAS_MEDIAPIPE:
            self.mp_pose = mp.solutions.pose
            self.pose = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,  # 0=light, 1=full
                smooth_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self.mp_drawing = mp.solutions.drawing_utils

            # Keypoint indices for key joints
            self.LEFT_SHOULDER = 11
            self.RIGHT_SHOULDER = 12
            self.LEFT_WRIST = 15
            self.RIGHT_WRIST = 16
            self.LEFT_HIP = 23
            self.RIGHT_HIP = 24
            self.NOSE = 0
        else:
            # Use optical flow fallback
            self.optical_detector = OpticalFlowBehaviorDetector()

    def _extract_frames(
        self,
        video_path: Union[str, Path],
        max_frames: int = 120,
        analysis_seconds: int = 10,
    ) -> List[np.ndarray]:
        """Extract frames from video."""
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        frames: List[np.ndarray] = []
        start_time = time.time()
        fps = capture.get(cv2.CAP_PROP_FPS) or 30

        while len(frames) < max_frames:
            ok, frame = capture.read()
            if not ok:
                break

            # Resize for faster processing
            h, w = frame.shape[:2]
            if w > 640:
                scale = 640 / w
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

            frames.append(frame)

            if analysis_seconds and (time.time() - start_time) >= analysis_seconds:
                break

        capture.release()

        if not frames:
            raise RuntimeError(f"No frames decoded from: {video_path}")

        return frames

    def _analyze_pose_keypoints(self, results) -> Optional[dict]:
        """Extract and return pose keypoints from MediaPipe results."""
        if not results.pose_landmarks:
            return None

        keypoints = {}
        for idx, lm in enumerate(results.pose_landmarks.landmark):
            if lm.visibility > 0.3:  # Only consider visible keypoints
                keypoints[idx] = (lm.x, lm.y, lm.z, lm.visibility)

        return keypoints

    def _calculate_motion_intensity(
        self,
        prev_keypoints: Optional[dict],
        curr_keypoints: Optional[dict],
    ) -> float:
        """Calculate overall motion intensity between frames."""
        if not prev_keypoints or not curr_keypoints:
            return 0.0

        distances: List[float] = []
        common_joints = set(prev_keypoints.keys()) & set(curr_keypoints.keys())

        for joint_idx in common_joints:
            prev_x, prev_y = prev_keypoints[joint_idx][:2]
            curr_x, curr_y = curr_keypoints[joint_idx][:2]
            distance = np.sqrt((curr_x - prev_x) ** 2 + (curr_y - prev_y) ** 2)
            distances.append(distance)

        if not distances:
            return 0.0

        # Normalize by typical human movement range
        avg_distance = np.mean(distances)
        return min(1.0, avg_distance * 3.0)  # Scale to 0-1 range

    def _calculate_arm_movement(
        self,
        keypoints: dict,
    ) -> float:
        """Calculate arm movement intensity."""
        if not keypoints:
            return 0.0

        # Check if wrists and shoulders are visible
        has_left_arm = (
            self.LEFT_SHOULDER in keypoints
            and self.LEFT_WRIST in keypoints
        )
        has_right_arm = (
            self.RIGHT_SHOULDER in keypoints
            and self.RIGHT_WRIST in keypoints
        )

        if not (has_left_arm or has_right_arm):
            return 0.0

        distances: List[float] = []

        if has_left_arm:
            sx, sy = keypoints[self.LEFT_SHOULDER][:2]
            wx, wy = keypoints[self.LEFT_WRIST][:2]
            dist = np.sqrt((wx - sx) ** 2 + (wy - sy) ** 2)
            distances.append(dist)

        if has_right_arm:
            sx, sy = keypoints[self.RIGHT_SHOULDER][:2]
            wx, wy = keypoints[self.RIGHT_WRIST][:2]
            dist = np.sqrt((wx - sx) ** 2 + (wy - sy) ** 2)
            distances.append(dist)

        avg_dist = np.mean(distances) if distances else 0.0
        # Normalize: typical arm length is ~0.3-0.4 of frame width
        return min(1.0, (avg_dist - 0.15) / 0.15) if avg_dist > 0.15 else 0.0

    def _detect_flapping_pattern(
        self,
        keypoint_history: List[dict],
    ) -> float:
        """
        Detect flapping/repetitive arm movements.
        Flapping is characterized by:
        - Vertical oscillation of wrists/elbows
        - High frequency (~2-3 Hz)
        - Similar amplitude over time
        """
        if len(keypoint_history) < 10:
            return 0.0

        # Extract vertical wrist positions
        wrist_ys: List[float] = []
        for kp in keypoint_history:
            if self.LEFT_WRIST in kp or self.RIGHT_WRIST in kp:
                if self.LEFT_WRIST in kp:
                    wrist_ys.append(kp[self.LEFT_WRIST][1])
                elif self.RIGHT_WRIST in kp:
                    wrist_ys.append(kp[self.RIGHT_WRIST][1])

        if len(wrist_ys) < 5:
            return 0.0

        wrist_ys = np.array(wrist_ys)

        # Calculate differences (rate of change)
        diffs = np.abs(np.diff(wrist_ys))
        mean_diff = np.mean(diffs)
        std_diff = np.std(diffs)

        # Flapping shows consistent, repeated motion (low variance relative to mean)
        if mean_diff > 0.01:
            repetition = 1.0 - min(1.0, std_diff / mean_diff) if mean_diff > 0 else 0.0
        else:
            repetition = 0.0

        return max(0.0, min(1.0, repetition))

    def _detect_spinning_pattern(
        self,
        keypoint_history: List[dict],
    ) -> float:
        """Detect rotational/spinning motion via shoulder-to-hip angle changes."""
        if len(keypoint_history) < 8:
            return 0.0
        angles = []
        for kp in keypoint_history:
            if (self.LEFT_SHOULDER in kp and self.RIGHT_SHOULDER in kp
                and self.LEFT_HIP in kp and self.RIGHT_HIP in kp):
                l_sh = kp[self.LEFT_SHOULDER][:2]
                r_sh = kp[self.RIGHT_SHOULDER][:2]
                l_hip = kp[self.LEFT_HIP][:2]
                r_hip = kp[self.RIGHT_HIP][:2]
                center_sh = ((l_sh[0] + r_sh[0]) / 2.0, (l_sh[1] + r_sh[1]) / 2.0)
                center_hip = ((l_hip[0] + r_hip[0]) / 2.0, (l_hip[1] + r_hip[1]) / 2.0)
                vx = center_sh[0] - center_hip[0]
                vy = center_sh[1] - center_hip[1]
                angle = np.arctan2(vy, vx)
                angles.append(angle)
        if len(angles) < 5:
            return 0.0
        angles = np.unwrap(np.array(angles))
        diffs = np.diff(angles)
        mean_speed = float(np.mean(np.abs(diffs)))
        std_speed = float(np.std(np.abs(diffs)))
        if mean_speed > 0.03:
            score = 1.0 - min(1.0, std_speed / (mean_speed + 1e-6))
        else:
            score = 0.0
        return max(0.0, min(1.0, score))

    def _detect_hiding_pattern(
        self,
        keypoint_history: List[dict],
    ) -> float:
        """Detect hiding or leaving-frame by monitoring keypoint visibility and nose presence."""
        if len(keypoint_history) < 5:
            return 0.0
        visible_counts = [len(kp) for kp in keypoint_history]
        nose_missing = sum(1 for kp in keypoint_history if self.NOSE not in kp)
        missing_ratio = nose_missing / len(keypoint_history)
        # If nose missing for large fraction of frames and visible keypoints drop, treat as hiding
        if missing_ratio > 0.35 or (np.mean(visible_counts) < 4):
            score = min(1.0, missing_ratio + (np.std(visible_counts) / (max(1, np.mean(visible_counts)) + 1e-6)))
        else:
            score = 0.0
        return max(0.0, min(1.0, score))

    def analyze_video(
        self,
        video_path: Union[str, Path],
        max_frames: int = 120,
        analysis_seconds: int = 10,
    ) -> MotionAnalysis:
        """Analyze video and detect behavior."""
        if not self.has_mediapipe:
            # Use optical flow fallback
            return self.optical_detector.analyze_video(
                video_path, max_frames, analysis_seconds
            )

        frames = self._extract_frames(video_path, max_frames, analysis_seconds)

        motion_intensities: List[float] = []
        arm_intensities: List[float] = []
        keypoint_history: List[dict] = []
        prev_keypoints: Optional[dict] = None

        for frame in frames:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)

            curr_keypoints = self._analyze_pose_keypoints(results)
            if curr_keypoints:
                keypoint_history.append(curr_keypoints)

                # Motion intensity
                motion_int = self._calculate_motion_intensity(prev_keypoints, curr_keypoints)
                motion_intensities.append(motion_int)

                # Arm movement
                arm_int = self._calculate_arm_movement(curr_keypoints)
                arm_intensities.append(arm_int)

                prev_keypoints = curr_keypoints

        if not motion_intensities:
            # No pose detected - classify as normal (calm, sitting)
            return MotionAnalysis(
                label="normal",
                confidence=0.6,
                motion_intensity=0.0,
                arm_movement_intensity=0.0,
                repetition_score=0.0,
                frames_analyzed=len(frames),
            )

        # Calculate aggregate metrics
        avg_motion = np.mean(motion_intensities)
        avg_arm_movement = np.mean(arm_intensities)
        max_arm_movement = np.max(arm_intensities) if arm_intensities else 0.0

        # Detect flapping/repetitive patterns
        flapping_score = self._detect_flapping_pattern(keypoint_history)

        # Detect spinning and hiding patterns
        spinning_score = self._detect_spinning_pattern(keypoint_history)
        hiding_score = self._detect_hiding_pattern(keypoint_history)

        # Classification logic
        # - High flapping score → "flapping" (stimming)
        # - High spinning score → "spinning" (rotational stimming)
        # - High hiding score → "hiding" (occlusion / leaving frame)
        # - High motion + high arm movement → "fight"
        # - Otherwise → "normal"

        is_flapping = flapping_score > 0.5
        is_spinning = spinning_score > 0.5
        is_hiding = hiding_score > 0.5
        is_intense = avg_motion > 0.4 and max_arm_movement > 0.5

        if is_flapping:
            label = "flapping"
            confidence = min(0.98, 0.6 + flapping_score * 0.4)

        elif is_spinning:
            label = "spinning"
            confidence = min(0.98, 0.6 + spinning_score * 0.4)

        elif is_hiding:
            label = "hiding"
            confidence = min(0.98, 0.6 + hiding_score * 0.4)

        elif is_intense and avg_motion > 0.3:
            label = "fight"
            confidence = min(0.95, 0.6 + avg_motion * 0.35)

        else:
            label = "normal"
            confidence = min(0.95, 0.7 + (1.0 - avg_motion) * 0.25)

        return MotionAnalysis(
            label=label,
            confidence=confidence,
            motion_intensity=avg_motion,
            arm_movement_intensity=avg_arm_movement,
            repetition_score=max(flapping_score, spinning_score),
            frames_analyzed=len(frames),
        )

    def __del__(self):
        """Cleanup MediaPipe resources."""
        if self.has_mediapipe and hasattr(self, 'pose'):
            self.pose.close()


def detect_behavior_motion_based(
    video_path: Union[str, Path],
    max_frames: int = 120,
    analysis_seconds: int = 10,
) -> Tuple[str, float]:
    """
    Convenience function to detect behavior from video using motion analysis.
    Uses MediaPipe Pose if available, otherwise falls back to optical flow.
    Returns (behavior_label, confidence).
    """
    try:
        try:
            detector = MotionBehaviorDetector()
            analysis = detector.analyze_video(video_path, max_frames, analysis_seconds)
            return analysis.label, analysis.confidence
        except Exception:
            # If MediaPipe-based detector fails (missing mediapipe or incompatible version),
            # use optical flow fallback directly.
            optical = OpticalFlowBehaviorDetector()
            analysis = optical.analyze_video(video_path, max_frames, analysis_seconds)
            return analysis.label, analysis.confidence
    except Exception as e:
        print(f"Motion-based behavior detection failed: {e}")
        # Final fallback: return normal behavior
        return "normal", 0.5

