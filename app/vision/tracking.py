"""
tracking.py
-----------
IoU-based multi-object tracker for frame-to-frame identity persistence.
Handles brief occlusions and prevents target switching between people.
"""

import numpy as np

from app.config.settings import TRACKER_MAX_LOST_FRAMES, TRACKER_IOU_THRESHOLD


def _iou(box_a, box_b):
    """Compute IoU between two (x1, y1, x2, y2) boxes."""
    xa = max(box_a[0], box_b[0])
    ya = max(box_a[1], box_b[1])
    xb = min(box_a[2], box_b[2])
    yb = min(box_a[3], box_b[3])

    inter = max(0, xb - xa) * max(0, yb - ya)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter

    return inter / union if union > 0 else 0.0


class Track:
    """Single tracked object with constant-velocity motion model."""
    __slots__ = ("track_id", "box", "confidence", "cx", "cy",
                 "vx", "vy", "lost_frames", "age")

    def __init__(self, track_id, box, confidence):
        x1, y1, x2, y2 = box
        self.track_id = track_id
        self.box = tuple(box)
        self.confidence = confidence
        self.cx = (x1 + x2) / 2.0
        self.cy = (y1 + y2) / 2.0
        self.vx = 0.0
        self.vy = 0.0
        self.lost_frames = 0
        self.age = 1

    def predict(self):
        """Predict next bbox position using velocity estimate."""
        w = self.box[2] - self.box[0]
        h = self.box[3] - self.box[1]
        pred_cx = self.cx + self.vx
        pred_cy = self.cy + self.vy
        return (pred_cx - w / 2, pred_cy - h / 2,
                pred_cx + w / 2, pred_cy + h / 2)

    def update(self, box, confidence):
        """Update track state with a matched detection."""
        x1, y1, x2, y2 = box
        new_cx = (x1 + x2) / 2.0
        new_cy = (y1 + y2) / 2.0
        # Exponential moving average for velocity
        alpha = 0.4
        self.vx = alpha * (new_cx - self.cx) + (1 - alpha) * self.vx
        self.vy = alpha * (new_cy - self.cy) + (1 - alpha) * self.vy
        self.cx = new_cx
        self.cy = new_cy
        self.box = tuple(box)
        self.confidence = confidence
        self.lost_frames = 0
        self.age += 1


class PersonTracker:
    """
    Multi-object tracker using greedy IoU matching with velocity prediction.
    Maintains persistent track IDs across frames.
    """

    def __init__(self):
        self.tracks = []
        self._next_id = 1
        self.locked_id = None   # user can lock onto a specific track

    def update(self, detections):
        """
        Match new detections to existing tracks.

        Args:
            detections: list of (x1, y1, x2, y2, confidence) tuples

        Returns:
            list of (track_id, x1, y1, x2, y2, confidence) for visible tracks
        """
        if not self.tracks and not detections:
            return []

        # Predict where each existing track should be
        predicted = [t.predict() for t in self.tracks]

        matched_det = set()
        matched_trk = set()

        if self.tracks and detections:
            n_trk = len(self.tracks)
            n_det = len(detections)
            iou_matrix = np.zeros((n_trk, n_det))
            for t_idx, pred_box in enumerate(predicted):
                for d_idx, det in enumerate(detections):
                    iou_matrix[t_idx, d_idx] = _iou(pred_box, det[:4])

            # Greedy matching: highest IoU pairs first
            for _ in range(min(n_trk, n_det)):
                if iou_matrix.size == 0:
                    break
                best = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
                t_idx, d_idx = int(best[0]), int(best[1])
                if iou_matrix[t_idx, d_idx] < TRACKER_IOU_THRESHOLD:
                    break
                matched_trk.add(t_idx)
                matched_det.add(d_idx)
                self.tracks[t_idx].update(detections[d_idx][:4],
                                          detections[d_idx][4])
                iou_matrix[t_idx, :] = 0
                iou_matrix[:, d_idx] = 0

        # Age unmatched tracks
        for t_idx, track in enumerate(self.tracks):
            if t_idx not in matched_trk:
                track.lost_frames += 1

        # Create new tracks for unmatched detections
        for d_idx, det in enumerate(detections):
            if d_idx not in matched_det:
                self.tracks.append(Track(self._next_id, det[:4], det[4]))
                self._next_id += 1

        # Remove dead tracks
        self.tracks = [t for t in self.tracks
                       if t.lost_frames <= TRACKER_MAX_LOST_FRAMES]

        # If locked track disappeared, unlock
        if self.locked_id is not None:
            if not any(t.track_id == self.locked_id for t in self.tracks):
                self.locked_id = None

        # Return only currently-visible tracks
        return [
            (t.track_id, *t.box, t.confidence)
            for t in self.tracks if t.lost_frames == 0
        ]

    def get_best_target(self, active_tracks):
        """
        Pick the best target from active tracks.
        If locked, return that track. Otherwise return the largest bbox.

        Returns:
            (track_id, x1, y1, x2, y2, conf) or None
        """
        if not active_tracks:
            return None

        # Prefer locked track
        if self.locked_id is not None:
            for t in active_tracks:
                if t[0] == self.locked_id:
                    return t

        # Otherwise pick largest bbox area
        return max(active_tracks,
                   key=lambda t: (t[3] - t[1]) * (t[4] - t[2]))

    def lock(self, track_id):
        """Lock onto a specific track ID."""
        self.locked_id = track_id

    def unlock(self):
        """Release track lock."""
        self.locked_id = None
