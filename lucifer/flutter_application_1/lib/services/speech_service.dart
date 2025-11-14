import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

class SpeechService {
  final Record _rec = Record();
  /// Start recording; caller should later call [stopRecording].
  Future<void> startRecording() async {
    if (!await _rec.hasPermission()) throw Exception('No mic permission');
    final dir = await getTemporaryDirectory();
    final path = p.join(dir.path, 'tmp_assistant_audio.wav');
    await _rec.start(path: path, encoder: AudioEncoder.wav, bitRate: 128000);
  }

  /// Stop recording and return the recorded file path.
  Future<String> stopRecording() async {
    final path = await _rec.stop();
    return path ?? '';
  }

  void dispose() { _rec.dispose(); }
}
