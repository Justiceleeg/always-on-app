"""Compatibility shim for torchaudio/SpeechBrain on newer torchaudio versions.

This module patches torchaudio to restore deprecated APIs that SpeechBrain depends on.
Must be imported BEFORE importing speechbrain.
"""

import torchaudio

# SpeechBrain 1.0.x uses list_audio_backends() which was removed in torchaudio 2.2+
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]

# SpeechBrain may also use set_audio_backend which was removed
if not hasattr(torchaudio, "set_audio_backend"):
    torchaudio.set_audio_backend = lambda backend: None

# SpeechBrain may use get_audio_backend which was removed
if not hasattr(torchaudio, "get_audio_backend"):
    torchaudio.get_audio_backend = lambda: "soundfile"
