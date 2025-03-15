import hashlib
from pathlib import Path

from fastlite import Database, Table

from geass.utils import Segment, Transcript

DB_PATH = Path.home() / ".geass.db"
DB_PATH.parent.mkdir(exist_ok=True)
db = Database(DB_PATH)

transcripts_t: Table = db.t.transcripts
segments_t: Table = db.t.segments
defaults_t: Table = db.t.defaults
cache_t: Table = db.t.cache


def create_tables():
    global transcripts_t, segments_t, defaults_t, cache_t
    if not transcripts_t.exists():
        transcripts_t.create(
            id=int,
            duration=str,
            file_path=str,
            start_time=float,
            end_time=float,
            pk="id",
        )

    if not segments_t.exists():
        segments_t.create(
            id=int,
            transcript_id=int,
            start=float,
            end=float,
            text=str,
            no_speech_prob=float,
            pk="id",
            foreign_keys=[("transcript_id", "transcripts", "id")],
        )

    if not defaults_t.exists():
        defaults_t.create(id=int, key=str, value=str, pk="id")
        defaults_t.insert({"key": "model_name", "value": "base"})
        defaults_t.insert({"key": "interval", "value": None})

    if not cache_t.exists():
        cache_t.create(
            file_hash=str,  # SHA-256 hash of the file
            transcript_id=int,
            pk="file_hash",
            foreign_keys=[("transcript_id", "transcripts", "id")],
        )


def _get_file_hash(file_path: Path) -> str:
    """Generate SHA-256 hash of file contents"""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_cached_transcript(file_path: Path) -> Transcript | None:
    """Check cache for existing transcription"""
    file_hash = _get_file_hash(file_path)
    cached = db.q(f"select * from cache where file_hash='{file_hash}'")
    if not cached:
        return None

    try:
        cache_entry = cached[0]
        transcript_row = transcripts_t[cache_entry["transcript_id"]]
        segments = [
            Segment(**s)
            for s in db.q(
                f"select * from segments where transcript_id='{transcript_row['id']}'"
            )
        ]

        return Transcript(
            duration=transcript_row["duration"],
            file_path=Path(transcript_row["file_path"]),
            segments=segments,
            start_time=transcript_row["start_time"],
            end_time=transcript_row["end_time"],
        )
    except (IndexError, KeyError):
        return None


def _save_transcript(t: Transcript) -> int:
    """Save a transcript and return its ID"""
    transcript_dict = {
        "duration": t.duration,
        "file_path": str(t.file_path),
        "start_time": t.start_time,
        "end_time": t.end_time,
    }
    return transcripts_t.insert(transcript_dict)["id"]


def _save_segments(transcript_id: int, segments: list[Segment]) -> None:
    """Save segments for a given transcript"""
    segment_dicts = [
        {
            "transcript_id": transcript_id,
            "start": s.start,
            "end": s.end,
            "text": s.text,
            "no_speech_prob": s.no_speech_prob,
        }
        for s in segments
    ]
    segments_t.insert_all(segment_dicts)


def save_transcription(t: Transcript) -> Transcript:
    """Save complete transcription and return transcript with ID"""
    try:
        transcript_id = _save_transcript(t)
        _save_segments(transcript_id, t.segments)

        file_hash = _get_file_hash(t.file_path)
        cache_t.insert(
            {
                "file_hash": file_hash,
                "transcript_id": transcript_id,
            }
        )
    except Exception as e:
        print(f"Error saving transcription: {e}")

    return t


def get_default(key: str) -> str | None:
    """Get default value for a key"""
    try:
        return defaults_t[db.q(f"select * from defaults where key='{key}'")[0]["id"]][
            "value"
        ]
    except (IndexError, KeyError):
        return None


def update_default(key: str, value: str) -> None:
    """Update or insert a default value"""
    existing = db.q(f"select * from defaults where key='{key}'")
    if existing:
        defaults_t.update(id=existing[0]["id"], value=value)
    else:
        defaults_t.insert(key=key, value=value)


create_tables()

DEFAULTS = {
    "model_name": get_default("model_name") or "base",
    "interval": get_default("interval") or None,
}
