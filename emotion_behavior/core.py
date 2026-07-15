from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

# Make cv2 and numpy optional to avoid import errors on headless/cloud environments
cv2 = None
np = None
try:
    import cv2 as _cv2
    import numpy as _np
    cv2 = _cv2
    np = _np
except (ImportError, OSError) as _err:
    print(f"[emotion_behavior.core] Optional dependency missing: {str(_err)}")
import torch
from PIL import Image
from torch import nn
from torch.utils.data import Dataset
from torchvision import models, transforms


EMOTION_LABELS: List[str] = [
    "angry",
    "disgust",
    "fear",
    "happy",
    "sad",
    "surprise",
    "neutral",
]

BEHAVIOR_LABELS: List[str] = ["normal", "fight"]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

# Map behavior predictions to emotional states for music recommendation
BEHAVIOR_TO_EMOTION: Dict[str, str] = {
    "normal": "calm",        # Normal behavior → calm mood
    "fight": "angry",        # Fighting/aggressive behavior → angry mood
    # Stimming and atypical behaviors should not be treated as 'calm' (no-op).
    # Map them to an active target so music is selected to help regulation.
    "flapping": "anxious",
    "spinning": "anxious",
    "hiding": "fearful",
}


@dataclass(frozen=True)
class EmotionPrediction:
    label: str
    confidence: float
    scores: Dict[str, float]


@dataclass(frozen=True)
class BehaviorPrediction:
    label: str
    confidence: float
    scores: Dict[str, float]
    frames_analyzed: int


def _resolve_device(device: Optional[str] = None) -> torch.device:
    if device:
        return torch.device(device)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _make_backbone(pretrained: bool = True) -> nn.Sequential:
    weights = models.MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
    network = models.mobilenet_v3_small(weights=weights)
    return nn.Sequential(network.features, network.avgpool, nn.Flatten())


def image_transforms(image_size: int = 224, train: bool = False) -> transforms.Compose:
    steps = [
        transforms.Resize((image_size, image_size)),
    ]
    if train:
        steps = [
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.Resize((image_size, image_size)),
        ]
    steps.extend(
        [
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    return transforms.Compose(steps)


class EmotionClassifier(nn.Module):
    def __init__(self, num_classes: int = len(EMOTION_LABELS), pretrained: bool = True):
        super().__init__()
        self.backbone = _make_backbone(pretrained=pretrained)
        self.head = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(576, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(256, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.backbone(x)
        return self.head(features)


class BehaviorClassifier(nn.Module):
    def __init__(self, num_classes: int = len(BEHAVIOR_LABELS), pretrained: bool = True):
        super().__init__()
        self.frame_encoder = _make_backbone(pretrained=pretrained)
        self.temporal = nn.GRU(
            input_size=576,
            hidden_size=256,
            batch_first=True,
            bidirectional=True,
        )
        self.head = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(512, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, time_steps, channels, height, width = x.shape
        frames = x.view(batch_size * time_steps, channels, height, width)
        encoded = self.frame_encoder(frames).view(batch_size, time_steps, -1)
        sequence, _ = self.temporal(encoded)
        pooled = sequence.mean(dim=1)
        return self.head(pooled)


class EmotionImageDataset(Dataset):
    def __init__(self, root: Union[str, Path], train: bool = False):
        self.root = Path(root)
        if not self.root.exists():
            raise FileNotFoundError(
                f"Emotion dataset folder not found: {self.root}. "
                "Create it and place RAF-DB images under class subfolders such as angry/, happy/, sad/."
            )
        self.transform = image_transforms(train=train)
        self.samples: List[Tuple[Path, int]] = []
        self.class_names = [label for label in EMOTION_LABELS if (self.root / label).exists()]
        if not self.class_names:
            self.class_names = sorted(
                [path.name for path in self.root.iterdir() if path.is_dir()]
            )
        self.class_to_idx = {name: index for index, name in enumerate(self.class_names)}
        for class_name in self.class_names:
            class_dir = self.root / class_name
            if not class_dir.exists():
                continue
            for path in class_dir.rglob("*"):
                if path.suffix.lower() in IMAGE_EXTENSIONS:
                    self.samples.append((path, self.class_to_idx[class_name]))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Tuple[torch.Tensor, int]:
        path, label = self.samples[index]
        image = Image.open(path).convert("RGB")
        return self.transform(image), label


class BehaviorVideoDataset(Dataset):
    def __init__(
        self,
        root: Union[str, Path],
        clip_len: int = 16,
        frame_stride: int = 2,
        train: bool = False,
    ):
        self.root = Path(root)
        if not self.root.exists():
            raise FileNotFoundError(
                f"Behavior dataset folder not found: {self.root}. "
                "This project uses a pretrained autism behavior detector checkpoint by default. "
                "Use a custom dataset only if you want to train your own model."
            )
        self.clip_len = clip_len
        self.frame_stride = frame_stride
        self.train = train
        self.transform = image_transforms(train=train)
        self.class_names = [label for label in BEHAVIOR_LABELS if (self.root / label).exists()]
        if not self.class_names:
            self.class_names = sorted(
                [path.name for path in self.root.iterdir() if path.is_dir()]
            )
        self.class_to_idx = {name: index for index, name in enumerate(self.class_names)}
        self.samples: List[Tuple[Path, int]] = []
        for class_name in self.class_names:
            class_dir = self.root / class_name
            if not class_dir.exists():
                continue
            for path in class_dir.rglob("*"):
                if path.suffix.lower() in VIDEO_EXTENSIONS:
                    self.samples.append((path, self.class_to_idx[class_name]))

    def __len__(self) -> int:
        return len(self.samples)

    def _read_clip(self, path: Path) -> torch.Tensor:
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise RuntimeError(f"Could not open video: {path}")

        frames: List[np.ndarray] = []
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total_frames <= 0:
            total_frames = self.clip_len * self.frame_stride

        if self.train:
            max_start = max(0, total_frames - (self.clip_len * self.frame_stride))
            start_index = int(torch.randint(0, max_start + 1, (1,)).item()) if max_start > 0 else 0
        else:
            start_index = 0

        for offset in range(self.clip_len):
            frame_index = start_index + offset * self.frame_stride
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = capture.read()
            if not ok:
                if frames:
                    frame = frames[-1].copy()
                else:
                    frame = np.zeros((224, 224, 3), dtype=np.uint8)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame_rgb)

        capture.release()

        clip_tensors = [self.transform(Image.fromarray(frame)) for frame in frames]
        return torch.stack(clip_tensors, dim=0)

    def __getitem__(self, index: int) -> Tuple[torch.Tensor, int]:
        path, label = self.samples[index]
        return self._read_clip(path), label


class EmotionPredictor:
    def __init__(self, checkpoint_path: Optional[Union[str, Path]] = None, device: Optional[str] = None):
        self.device = _resolve_device(device)
        self.model = EmotionClassifier(pretrained=False).to(self.device)
        self.model.eval()
        self.labels = EMOTION_LABELS
        if checkpoint_path:
            self.load(checkpoint_path)

    def load(self, checkpoint_path: Union[str, Path]) -> None:
        path = Path(checkpoint_path)
        if not path.exists():
            raise FileNotFoundError(path)
        checkpoint = torch.load(path, map_location=self.device)
        state_dict = checkpoint.get("model_state", checkpoint)
        self.model.load_state_dict(state_dict)
        self.labels = checkpoint.get("class_names", self.labels)
        self.model.eval()

    def predict_tensor(self, image_tensor: torch.Tensor) -> EmotionPrediction:
        with torch.no_grad():
            logits = self.model(image_tensor.unsqueeze(0).to(self.device))
            probabilities = torch.softmax(logits, dim=-1)[0].cpu().numpy()
        best_index = int(np.argmax(probabilities))
        scores = {label: float(probabilities[index]) for index, label in enumerate(self.labels)}
        return EmotionPrediction(label=self.labels[best_index], confidence=float(probabilities[best_index]), scores=scores)

    def predict_bgr(self, frame_bgr: np.ndarray) -> EmotionPrediction:
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)
        tensor = image_transforms(train=False)(image)
        return self.predict_tensor(tensor)


class BehaviorPredictor:
    def __init__(self, checkpoint_path: Optional[Union[str, Path]] = None, device: Optional[str] = None):
        self.device = _resolve_device(device)
        self.model = BehaviorClassifier(pretrained=False).to(self.device)
        self.model.eval()
        self.labels = BEHAVIOR_LABELS
        if checkpoint_path:
            self.load(checkpoint_path)

    def load(self, checkpoint_path: Union[str, Path]) -> None:
        path = Path(checkpoint_path)
        if not path.exists():
            raise FileNotFoundError(path)
        checkpoint = torch.load(path, map_location=self.device)
        state_dict = checkpoint.get("model_state", checkpoint)
        self.model.load_state_dict(state_dict)
        self.labels = checkpoint.get("class_names", self.labels)
        self.model.eval()

    def predict_clip_tensor(self, clip_tensor: torch.Tensor) -> BehaviorPrediction:
        with torch.no_grad():
            logits = self.model(clip_tensor.unsqueeze(0).to(self.device))
            probabilities = torch.softmax(logits, dim=-1)[0].cpu().numpy()
        best_index = int(np.argmax(probabilities))
        scores = {label: float(probabilities[index]) for index, label in enumerate(self.labels)}
        return BehaviorPrediction(
            label=self.labels[best_index],
            confidence=float(probabilities[best_index]),
            scores=scores,
            frames_analyzed=int(clip_tensor.shape[0]),
        )

    def _read_frames(self, source: Union[str, Path], max_frames: int = 64, analysis_seconds: int = 10) -> List[np.ndarray]:
        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            raise RuntimeError(f"Could not open video source: {source}")
        frames: List[np.ndarray] = []
        start_time = time.time()
        while len(frames) < max_frames:
            ok, frame = capture.read()
            if not ok:
                break
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if analysis_seconds and (time.time() - start_time) >= analysis_seconds:
                break
        capture.release()
        if not frames:
            raise RuntimeError(f"No frames decoded from source: {source}")
        return frames

    def _frames_to_clip(self, frames: Sequence[np.ndarray], clip_len: int = 16) -> torch.Tensor:
        if len(frames) < clip_len:
            frames = list(frames) + [frames[-1]] * (clip_len - len(frames))
        indices = np.linspace(0, len(frames) - 1, clip_len).astype(int)
        clip = [image_transforms(train=False)(Image.fromarray(frames[index])) for index in indices]
        return torch.stack(clip, dim=0)

    def predict_source(
        self,
        source: Union[str, Path],
        clip_len: int = 16,
        max_frames: int = 64,
        analysis_seconds: int = 10,
        max_clips: int = 4,
    ) -> BehaviorPrediction:
        frames = self._read_frames(source, max_frames=max_frames, analysis_seconds=analysis_seconds)
        if len(frames) <= clip_len:
            return self.predict_clip_tensor(self._frames_to_clip(frames, clip_len=clip_len))

        window_size = max(clip_len, len(frames) // max_clips)
        clip_predictions: List[BehaviorPrediction] = []
        for start_index in range(0, len(frames), window_size):
            clip_frames = frames[start_index : start_index + window_size]
            if len(clip_frames) < clip_len:
                break
            clip_tensor = self._frames_to_clip(clip_frames, clip_len=clip_len)
            clip_predictions.append(self.predict_clip_tensor(clip_tensor))
            if len(clip_predictions) >= max_clips:
                break

        if not clip_predictions:
            return self.predict_clip_tensor(self._frames_to_clip(frames, clip_len=clip_len))

        averaged_scores: Dict[str, float] = {label: 0.0 for label in self.labels}
        for prediction in clip_predictions:
            for label, score in prediction.scores.items():
                averaged_scores[label] = averaged_scores.get(label, 0.0) + float(score)
        for label in averaged_scores:
            averaged_scores[label] /= len(clip_predictions)
        best_label = max(averaged_scores.items(), key=lambda item: item[1])[0]
        return BehaviorPrediction(
            label=best_label,
            confidence=float(averaged_scores[best_label]),
            scores=averaged_scores,
            frames_analyzed=len(frames),
        )


_EMOTION_PREDICTOR: Optional[EmotionPredictor] = None
_BEHAVIOR_PREDICTOR: Optional[BehaviorPredictor] = None


def load_emotion_predictor(checkpoint_path: Optional[Union[str, Path]] = None) -> Optional[EmotionPredictor]:
    global _EMOTION_PREDICTOR
    if _EMOTION_PREDICTOR is not None:
        return _EMOTION_PREDICTOR
    default_path = Path(checkpoint_path or os.getenv("EMOTION_MODEL_PATH", "artifacts/emotion_model.pt"))
    if not default_path.exists():
        return None
    _EMOTION_PREDICTOR = EmotionPredictor(default_path)
    return _EMOTION_PREDICTOR


def load_behavior_predictor(checkpoint_path: Optional[Union[str, Path]] = None) -> Optional[BehaviorPredictor]:
    global _BEHAVIOR_PREDICTOR
    if _BEHAVIOR_PREDICTOR is not None:
        return _BEHAVIOR_PREDICTOR
    default_path = Path(checkpoint_path or os.getenv("BEHAVIOR_MODEL_PATH", "artifacts/behavior_model.pt"))
    if not default_path.exists():
        return None
    _BEHAVIOR_PREDICTOR = BehaviorPredictor(default_path)
    return _BEHAVIOR_PREDICTOR


def detect_emotion_from_bgr(frame_bgr: np.ndarray) -> Optional[EmotionPrediction]:
    try:
        predictor = load_emotion_predictor()
        if predictor is None:
            return None
        return predictor.predict_bgr(frame_bgr)
    except Exception:
        return None


def detect_behavior_from_source(
    source: Union[str, Path],
    *,
    clip_len: int = 16,
    max_frames: int = 64,
    analysis_seconds: int = 10,
    max_clips: int = 4,
) -> BehaviorPrediction:
    predictor = load_behavior_predictor()
    if predictor is not None:
        return predictor.predict_source(
            source,
            clip_len=clip_len,
            max_frames=max_frames,
            analysis_seconds=analysis_seconds,
            max_clips=max_clips,
        )
    
    # Fallback: Use motion-based behavior detection (MediaPipe Pose)
    # This detects flapping, arm movements, and overall activity intensity
    try:
        from .motion_detector import detect_behavior_motion_based
        label, confidence = detect_behavior_motion_based(
            source,
            max_frames=max_frames,
            analysis_seconds=analysis_seconds,
        )
        # Provide scores for possible fallback labels
        scores = {
            "normal": 0.0,
            "fight": 0.0,
            "flapping": 0.0,
            "spinning": 0.0,
            "hiding": 0.0,
        }
        scores[label] = float(confidence)
        # For remaining keys, distribute residual probability
        residual = max(0.0, 1.0 - float(confidence))
        num_other = max(1, len(scores) - 1)
        for k in scores:
            if k != label:
                scores[k] = float(residual / num_other)

        return BehaviorPrediction(
            label=label,
            confidence=confidence,
            scores=scores,
            frames_analyzed=max_frames,
        )
    except Exception as e:
        print(f"Behavior detection fallback failed: {e}")
        # Final fallback: assume normal/calm behavior
        return BehaviorPrediction(
            label="normal",
            confidence=0.5,
            scores={"normal": 0.5, "fight": 0.5},
            frames_analyzed=0,
        )
