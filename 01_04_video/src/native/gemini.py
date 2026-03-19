# -*- coding: utf-8 -*-

#   gemini.py

"""
### Description:
Google Gemini API wrapper for video processing. Uses gemini-2.5-flash for video
understanding. All API calls are direct REST requests via httpx (no Google SDK).

Provides:
- upload_video_file()  — resumable upload for large files (>20 MB)
- process_video()      — core Gemini generateContent call
- analyze_video()      — structured analysis with JSON schema
- transcribe_video()   — speech transcription with timestamps/speakers
- extract_from_video() — scene / keyframe / object / text extraction

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/native/gemini.js`


"""

import json
import logging
from typing import Any

import httpx

from ..config import gemini
from ..helpers.logger import log
from ..helpers.stats import record_gemini

logger = logging.getLogger(__name__)

UPLOAD_ENDPOINT = "https://generativelanguage.googleapis.com/upload/v1beta/files"
GENERATE_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{gemini.video_model}:generateContent"
)


async def upload_video_file(
    video_bytes: bytes,
    mime_type: str,
    display_name: str,
) -> dict[str, str]:
    """Upload a video file to Gemini Files API via the resumable upload protocol.

    Required for files > 20 MB or when reusing the same file across requests.

    The resumable protocol is two sequential POST requests:
    1. Init: sends metadata → receives the upload URL in the response header.
    2. Upload: streams the binary bytes to the upload URL → receives file metadata.

    Args:
        video_bytes: Raw video file content.
        mime_type: MIME type of the video (e.g. ``"video/mp4"``).
        display_name: Human-readable name stored in Gemini Files.

    Returns:
        Dict with ``file_uri``, ``name``, and ``mime_type`` of the uploaded file.

    Raises:
        RuntimeError: On any API failure or missing response fields.
    """
    log.gemini("Uploading video file", display_name)

    async with httpx.AsyncClient(timeout=600.0) as client:
        # Step 1: Initialize the resumable upload session
        init_resp = await client.post(
            UPLOAD_ENDPOINT,
            headers={
                "x-goog-api-key": gemini.api_key,
                "X-Goog-Upload-Protocol": "resumable",
                "X-Goog-Upload-Command": "start",
                "X-Goog-Upload-Header-Content-Length": str(len(video_bytes)),
                "X-Goog-Upload-Header-Content-Type": mime_type,
                "Content-Type": "application/json",
            },
            content=json.dumps({"file": {"display_name": display_name}}).encode(),
        )
        if not init_resp.is_success:
            raise RuntimeError(f"Upload init failed: {init_resp.text}")

        upload_url = init_resp.headers.get("x-goog-upload-url")
        if not upload_url:
            raise RuntimeError("No upload URL received from Gemini")

        # Step 2: Stream the actual bytes to the upload URL
        upload_resp = await client.post(
            upload_url,
            headers={
                "Content-Length": str(len(video_bytes)),
                "X-Goog-Upload-Offset": "0",
                "X-Goog-Upload-Command": "upload, finalize",
            },
            content=video_bytes,
        )
        if not upload_resp.is_success:
            raise RuntimeError(f"Upload failed: {upload_resp.text}")

        file_info = upload_resp.json()

    if not file_info.get("file", {}).get("uri"):
        raise RuntimeError("No file URI in upload response")

    log.gemini_result(True, f"Uploaded: {file_info['file']['name']}")
    record_gemini("upload")

    return {
        "file_uri": file_info["file"]["uri"],
        "name": file_info["file"]["name"],
        "mime_type": file_info["file"].get("mimeType", mime_type),
    }


async def process_video(
    *,
    file_uri: str | None = None,
    video_base64: str | None = None,
    mime_type: str | None = None,
    prompt: str,
    response_schema: dict[str, Any] | None = None,
    video_metadata: dict[str, Any] | None = None,
) -> str | dict[str, Any]:
    """Send a video to Gemini and return the model's response.

    Accepts either an uploaded file URI (including YouTube URLs) or base64-encoded
    inline video data. Appends the text prompt after the video part, as recommended
    by the Gemini docs.

    Args:
        file_uri: Uploaded Gemini Files URI or a YouTube URL.
        video_base64: Base64-encoded video bytes (for files <= 20 MB).
        mime_type: MIME type of the video.
        prompt: Instruction text sent to the model.
        response_schema: Optional Gemini JSON schema for structured output.
        video_metadata: Optional ``{ start_offset, end_offset, fps }`` for clipping.

    Returns:
        Parsed JSON object when ``response_schema`` is provided, otherwise raw text.

    Raises:
        ValueError: When neither ``file_uri`` nor ``video_base64`` is provided.
        RuntimeError: On Gemini API error or empty response.
    """
    log.gemini("Processing video", prompt[:80])

    parts: list[dict[str, Any]] = []

    if file_uri:
        file_part: dict[str, Any] = {"file_data": {"file_uri": file_uri}}
        # YouTube URLs must omit mime_type — Gemini infers it from the URL
        if "youtube.com" not in file_uri and "youtu.be" not in file_uri:
            file_part["file_data"]["mime_type"] = mime_type
        if video_metadata:
            file_part["video_metadata"] = video_metadata
        parts.append(file_part)
    elif video_base64:
        inline_part: dict[str, Any] = {
            "inline_data": {"mime_type": mime_type, "data": video_base64}
        }
        if video_metadata:
            inline_part["video_metadata"] = video_metadata
        parts.append(inline_part)
    else:
        raise ValueError("Either file_uri or video_base64 must be provided")

    # Text prompt comes after the video (best practice per Gemini docs)
    parts.append({"text": prompt})

    body: dict[str, Any] = {"contents": [{"parts": parts}]}
    if response_schema:
        body["generation_config"] = {
            "response_mime_type": "application/json",
            "response_schema": response_schema,
        }

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            GENERATE_ENDPOINT,
            headers={
                "x-goog-api-key": gemini.api_key,
                "Content-Type": "application/json",
            },
            json=body,
        )

    if not resp.is_success:
        raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")

    data = resp.json()

    if data.get("error"):
        err = data["error"]
        raise RuntimeError(err.get("message") or json.dumps(err))

    record_gemini("process")

    text: str | None = (
        (data.get("candidates") or [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text")
    )
    if not text:
        raise RuntimeError("No text response from Gemini")

    log.gemini_result(True, f"Processed video ({len(text)} chars)")

    if response_schema:
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return text

    return text


async def analyze_video(
    *,
    file_uri: str | None = None,
    video_base64: str | None = None,
    mime_type: str | None = None,
    analysis_type: str = "general",
    custom_prompt: str | None = None,
    video_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Analyze video content (visual, audio, action, or general).

    Args:
        file_uri: Uploaded file URI or YouTube URL.
        video_base64: Base64 video data (alternative to ``file_uri``).
        mime_type: MIME type of the video.
        analysis_type: One of ``"general"``, ``"visual"``, ``"audio"``, ``"action"``.
        custom_prompt: Override the default prompt for the chosen analysis type.
        video_metadata: Optional clipping / FPS settings.

    Returns:
        Structured analysis dict matching the Gemini response schema.
    """
    prompts = {
        "general": (
            "Analyze this video comprehensively. Describe:\n"
            "- Type of video content (tutorial, vlog, presentation, movie clip, etc.)\n"
            "- Main subject and topics covered\n"
            "- Key visual elements and scenes\n"
            "- Audio content (speech, music, sound effects)\n"
            "- Overall quality and production value\n"
            "- Notable moments with timestamps (MM:SS format)"
        ),
        "visual": (
            "Analyze the visual elements of this video. Describe:\n"
            "- Scene composition and cinematography\n"
            "- Color palette and lighting\n"
            "- Text overlays, graphics, or animations\n"
            "- Objects and people visible\n"
            "- Visual transitions and effects\n"
            "- Key visual moments with timestamps"
        ),
        "audio": (
            "Analyze the audio content of this video. Describe:\n"
            "- Speech content and speakers\n"
            "- Background music (genre, mood)\n"
            "- Sound effects\n"
            "- Audio quality\n"
            "- Key audio moments with timestamps"
        ),
        "action": (
            "Analyze the actions and events in this video. Describe:\n"
            "- Sequence of events with timestamps\n"
            "- Key actions performed\n"
            "- Interactions between subjects\n"
            "- Important transitions or changes\n"
            "- Climactic or significant moments"
        ),
    }

    prompt = custom_prompt or prompts.get(analysis_type, prompts["general"])

    schema: dict[str, Any] = {
        "type": "OBJECT",
        "properties": {
            "video_type": {"type": "STRING", "description": "Type of video content"},
            "summary": {"type": "STRING", "description": "Brief summary of the video"},
            "duration_estimate": {
                "type": "STRING",
                "description": "Estimated duration of the video",
            },
            "key_moments": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "timestamp": {
                            "type": "STRING",
                            "description": "Timestamp in MM:SS format",
                        },
                        "description": {
                            "type": "STRING",
                            "description": "What happens at this moment",
                        },
                    },
                },
                "description": "Key moments with timestamps",
            },
            "visual_elements": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "Notable visual elements",
            },
            "audio_elements": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "Notable audio elements",
            },
            "quality_assessment": {
                "type": "STRING",
                "description": "Video quality assessment",
            },
        },
        "required": ["video_type", "summary"],
    }

    return await process_video(
        file_uri=file_uri,
        video_base64=video_base64,
        mime_type=mime_type,
        prompt=prompt,
        response_schema=schema,
        video_metadata=video_metadata,
    )


async def transcribe_video(
    *,
    file_uri: str | None = None,
    video_base64: str | None = None,
    mime_type: str | None = None,
    include_timestamps: bool = True,
    detect_speakers: bool = True,
    target_language: str | None = None,
    video_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Transcribe speech from a video with timestamps and speaker labels.

    Args:
        file_uri: Uploaded file URI or YouTube URL.
        video_base64: Base64 video data (alternative).
        mime_type: MIME type of the video.
        include_timestamps: Whether to include MM:SS timestamps per segment.
        detect_speakers: Whether to label distinct speakers.
        target_language: If set, translate all segments to this language.
        video_metadata: Optional clipping settings.

    Returns:
        Structured transcription dict matching the Gemini response schema.
    """
    prompt = "Transcribe all speech from this video.\n\nRequirements:\n"
    if detect_speakers:
        prompt += (
            "- Identify distinct speakers "
            "(e.g., Speaker 1, Speaker 2, or names if visible/mentioned).\n"
        )
    if include_timestamps:
        prompt += "- Provide accurate timestamps for each segment (Format: MM:SS).\n"
    prompt += "- Detect the primary language.\n"
    if target_language:
        prompt += f"- Translate all segments to {target_language}.\n"
    prompt += "- Note any significant non-speech audio (music, sound effects) with timestamps.\n"
    prompt += "- Provide a brief summary at the beginning."

    # Build segment properties dynamically based on options
    segment_props: dict[str, Any] = {
        "speaker": {"type": "STRING"},
        "timestamp": {"type": "STRING"},
        "content": {"type": "STRING"},
    }
    if target_language:
        segment_props["translation"] = {"type": "STRING"}

    segment_required = ["content"]
    if include_timestamps:
        segment_required.append("timestamp")
    if detect_speakers:
        segment_required.append("speaker")

    schema: dict[str, Any] = {
        "type": "OBJECT",
        "properties": {
            "summary": {
                "type": "STRING",
                "description": "A concise summary of the spoken content.",
            },
            "duration_estimate": {
                "type": "STRING",
                "description": "Estimated duration of the video.",
            },
            "primary_language": {
                "type": "STRING",
                "description": "Primary language detected.",
            },
            "segments": {
                "type": "ARRAY",
                "description": "List of transcribed segments.",
                "items": {
                    "type": "OBJECT",
                    "properties": segment_props,
                    "required": segment_required,
                },
            },
            "non_speech_audio": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "timestamp": {"type": "STRING"},
                        "description": {"type": "STRING"},
                    },
                },
                "description": "Notable non-speech audio moments",
            },
        },
        "required": ["summary", "segments"],
    }

    return await process_video(
        file_uri=file_uri,
        video_base64=video_base64,
        mime_type=mime_type,
        prompt=prompt,
        response_schema=schema,
        video_metadata=video_metadata,
    )


async def extract_from_video(
    *,
    file_uri: str | None = None,
    video_base64: str | None = None,
    mime_type: str | None = None,
    extraction_type: str = "scenes",
    video_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract structured elements from a video (scenes, keyframes, objects, text).

    Args:
        file_uri: Uploaded file URI or YouTube URL.
        video_base64: Base64 video data (alternative).
        mime_type: MIME type of the video.
        extraction_type: One of ``"scenes"``, ``"keyframes"``, ``"objects"``, ``"text"``.
        video_metadata: Optional clipping / FPS settings.

    Returns:
        Structured extraction dict matching the Gemini response schema.
    """
    prompts = {
        "scenes": (
            "Identify and describe all distinct scenes in this video.\n"
            "For each scene provide:\n"
            "- Start timestamp (MM:SS)\n"
            "- End timestamp (MM:SS)\n"
            "- Description of the scene\n"
            "- Key visual elements\n"
            "- Mood/tone"
        ),
        "keyframes": (
            "Identify the key frames in this video - moments that best represent the content.\n"
            "For each keyframe provide:\n"
            "- Timestamp (MM:SS)\n"
            "- Description of what's shown\n"
            "- Why this frame is significant"
        ),
        "objects": (
            "Identify all notable objects, people, and elements visible in this video.\n"
            "For each item provide:\n"
            "- What it is\n"
            "- Timestamps when visible (MM:SS)\n"
            "- Context/relevance to the video"
        ),
        "text": (
            "Extract all text visible in this video "
            "(on-screen text, titles, captions, signs, etc.)\n"
            "For each text element provide:\n"
            "- The text content\n"
            "- Timestamp when visible (MM:SS)\n"
            "- Location on screen\n"
            "- Purpose (title, caption, sign, etc.)"
        ),
    }

    schemas: dict[str, dict[str, Any]] = {
        "scenes": {
            "type": "OBJECT",
            "properties": {
                "total_scenes": {"type": "INTEGER"},
                "scenes": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "scene_number": {"type": "INTEGER"},
                            "start_time": {"type": "STRING"},
                            "end_time": {"type": "STRING"},
                            "description": {"type": "STRING"},
                            "visual_elements": {
                                "type": "ARRAY",
                                "items": {"type": "STRING"},
                            },
                            "mood": {"type": "STRING"},
                        },
                    },
                },
            },
        },
        "keyframes": {
            "type": "OBJECT",
            "properties": {
                "total_keyframes": {"type": "INTEGER"},
                "keyframes": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "timestamp": {"type": "STRING"},
                            "description": {"type": "STRING"},
                            "significance": {"type": "STRING"},
                        },
                    },
                },
            },
        },
        "objects": {
            "type": "OBJECT",
            "properties": {
                "objects": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "name": {"type": "STRING"},
                            "timestamps": {
                                "type": "ARRAY",
                                "items": {"type": "STRING"},
                            },
                            "context": {"type": "STRING"},
                        },
                    },
                }
            },
        },
        "text": {
            "type": "OBJECT",
            "properties": {
                "text_elements": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "content": {"type": "STRING"},
                            "timestamp": {"type": "STRING"},
                            "location": {"type": "STRING"},
                            "purpose": {"type": "STRING"},
                        },
                    },
                }
            },
        },
    }

    prompt = prompts.get(extraction_type, prompts["scenes"])
    schema = schemas.get(extraction_type, schemas["scenes"])

    return await process_video(
        file_uri=file_uri,
        video_base64=video_base64,
        mime_type=mime_type,
        prompt=prompt,
        response_schema=schema,
        video_metadata=video_metadata,
    )
