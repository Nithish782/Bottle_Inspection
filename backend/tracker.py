"""
Lightweight centroid-based bottle tracker.
Assigns stable IDs across frames so bounding boxes don't flicker.
"""
import numpy as np
from config import TRACKER_MAX_AGE


class Track:
    _next_id = 1

    def __init__(self, bottle):
        self.id       = Track._next_id
        Track._next_id += 1
        self.bottle   = bottle
        self.age      = 0          # frames since last matched
        self.hits     = 1

    @property
    def centroid(self):
        b = self.bottle["box"]
        return np.array([(b[0]+b[2])/2, (b[1]+b[3])/2])


class BottleTracker:
    def __init__(self, max_age=TRACKER_MAX_AGE, max_dist=80):
        self.tracks   = []
        self.max_age  = max_age
        self.max_dist = max_dist   # pixels — max centroid distance to match

    def update(self, bottles):
        """
        Match new detections to existing tracks using centroid distance.
        Returns the updated bottle list with stable 'id' fields.
        """
        if not bottles:
            for t in self.tracks:
                t.age += 1
            self.tracks = [t for t in self.tracks if t.age <= self.max_age]
            return []

        if not self.tracks:
            for b in bottles:
                self.tracks.append(Track(b))
            return self._export(bottles)

        # Build cost matrix (centroid distance)
        track_cents = np.array([t.centroid for t in self.tracks])
        det_cents   = np.array([
            [(b["box"][0]+b["box"][2])/2, (b["box"][1]+b["box"][3])/2]
            for b in bottles
        ])

        cost = np.linalg.norm(
            track_cents[:, None] - det_cents[None, :], axis=2
        )  # (num_tracks, num_dets)

        matched_t, matched_d = set(), set()
        if cost.size:
            for _ in range(min(len(self.tracks), len(bottles))):
                idx = np.argmin(cost)
                ti, di = divmod(idx, cost.shape[1])
                if cost[ti, di] > self.max_dist:
                    break
                matched_t.add(ti); matched_d.add(di)
                self.tracks[ti].bottle = bottles[di]
                self.tracks[ti].age    = 0
                self.tracks[ti].hits  += 1
                cost[ti, :] = 1e9
                cost[:, di] = 1e9

        # Age unmatched tracks
        for i, t in enumerate(self.tracks):
            if i not in matched_t:
                t.age += 1

        # Create new tracks for unmatched detections
        for j, b in enumerate(bottles):
            if j not in matched_d:
                self.tracks.append(Track(b))

        # Prune dead tracks
        self.tracks = [t for t in self.tracks if t.age <= self.max_age]

        return self._export(bottles)

    def _export(self, bottles):
        """Attach stable track IDs to bottle dicts."""
        result = []
        for t in self.tracks:
            if t.age == 0:
                b = dict(t.bottle)
                b["id"] = t.id
                result.append(b)
        return result


tracker = BottleTracker()