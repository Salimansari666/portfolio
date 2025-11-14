import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';

class TtsService {
  final AudioPlayer _player = AudioPlayer();

  /// Play raw audio bytes (e.g., WAV/MP3) returned by a TTS provider.
  Future<void> playBytes(Uint8List bytes, {String mime = 'audio/wav'}) async {
    try {
      final uri = Uri.dataFromBytes(bytes, mimeType: mime);
      await _player.setAudioSource(AudioSource.uri(uri));
      await _player.play();
    } catch (e) {
      debugPrint('TTS playBytes error: $e');
    }
  }

  Future<void> dispose() async {
    await _player.dispose();
  }
}
