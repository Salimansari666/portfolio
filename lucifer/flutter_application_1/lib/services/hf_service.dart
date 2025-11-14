import 'dart:convert';
import 'dart:io';
// 'Uint8List' is available from foundation.dart; no direct typed_data import needed.
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class HfService {
  final String apiToken;
  HfService({required this.apiToken});
  Map<String, String> get _headers => {
    'Authorization': 'Bearer $apiToken',
  };

  // ASR using whisper model endpoint (example):
  Future<String?> asr(File audioFile) async {
    final uri = Uri.parse('https://api-inference.huggingface.co/models/openai/whisper-large-v2'); // or other ASR model
    final bytes = await audioFile.readAsBytes();
    final resp = await http.post(uri, headers: {
      ..._headers,
      'Content-Type': 'audio/wav'
    }, body: bytes);
    if (resp.statusCode == 200) {
      final decoded = jsonDecode(resp.body);
      // HF ASR sometimes returns {"text":"..."}; check model response
      return decoded['text'] ?? decoded.toString();
    } else {
      debugPrint('ASR error: ${resp.statusCode} ${resp.body}');
      return null;
    }
  }

  // Simple text generation
  Future<String?> textGeneration(String prompt) async {
    final uri = Uri.parse('https://api-inference.huggingface.co/models/gpt2'); // replace with chosen model
    final resp = await http.post(uri, headers: {
      ..._headers,
      'Content-Type': 'application/json'
    }, body: jsonEncode({'inputs': prompt, 'parameters': {'max_new_tokens': 200}}));
    if (resp.statusCode == 200) {
      final decoded = jsonDecode(resp.body);
      // Many HF text models return list or dict — handle both:
      if (decoded is List && decoded.isNotEmpty && decoded[0]['generated_text'] != null) {
        return decoded[0]['generated_text'];
      } else if (decoded is Map && decoded['generated_text'] != null) {
        return decoded['generated_text'];
      } else {
        return decoded.toString();
      }
    } else {
      debugPrint('Text gen error: ${resp.statusCode} ${resp.body}');
      return null;
    }
  }

  // Example VQA: send image + question
  Future<String?> vqa(File image, String question) async {
    final uri = Uri.parse('https://api-inference.huggingface.co/models/nlpconnect/vit-gpt2-image-captioning'); // sample multimodal
    final bytes = await image.readAsBytes();
    final request = http.MultipartRequest('POST', uri);
    request.headers.addAll({'Authorization': 'Bearer $apiToken'});
    final multipart = http.MultipartFile.fromBytes('file', bytes, filename: 'upload.jpg');
    request.files.add(multipart);
    request.fields['inputs'] = question;
    final streamed = await request.send();
    final resp = await http.Response.fromStream(streamed);
    if (resp.statusCode == 200) {
      final decoded = jsonDecode(resp.body);
      // handle response format
      if (decoded is List && decoded.isNotEmpty) return decoded[0].toString();
      return decoded.toString();
    } else {
      debugPrint('VQA error: ${resp.statusCode} ${resp.body}');
      return null;
    }
  }

  // TTS via HF example (model that returns audio)
  Future<Uint8List?> tts(String text) async {
    final uri = Uri.parse('https://api-inference.huggingface.co/models/facebook/tts_transformer'); // replace with real TTS model
    final resp = await http.post(uri, headers: {
      ..._headers,
      'Content-Type': 'application/json'
    }, body: jsonEncode({'inputs': text}));
    if (resp.statusCode == 200) {
      // HF may return audio bytes or encoded structure
      return resp.bodyBytes;
    } else {
      debugPrint('TTS error: ${resp.statusCode} ${resp.body}');
      return null;
    }
  }
}
