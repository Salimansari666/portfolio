import 'dart:io';
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:image_picker/image_picker.dart';
import 'services/speech_service.dart';
import 'services/hf_service.dart';
import 'services/native_control.dart';
import 'services/tts_service.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env');
  // Init Firebase here if you will: await Firebase.initializeApp();
  runApp(MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  final SpeechService speech = SpeechService();
  final HfService hf = HfService(apiToken: dotenv.env['HF_API_TOKEN'] ?? '');
  final NativeControl nativeControl = NativeControl();
  final TtsService tts = TtsService();
  String transcript = '';
  String assistantResponse = '';

  @override
  void dispose() {
    speech.dispose();
    tts.dispose();
    super.dispose();
  }

  Future<void> askHfForText(String text) async {
    setState(() => assistantResponse = 'Thinking...');
    final res = await hf.textGeneration(text);
    setState(() => assistantResponse = res ?? 'No response');
    if (res != null) {
      final audio = await hf.tts(res);
      if (audio != null) {
        await tts.playBytes(audio);
      } else {
        debugPrint('No TTS audio available, response: $res');
      }
    }
  }

  Future<void> sendImageForVQA(File image, String question) async {
    setState(() => assistantResponse = 'Working on image...');
    final res = await hf.vqa(image, question);
    setState(() => assistantResponse = res ?? 'No answer');
    if (res != null) {
      final audio = await hf.tts(res);
      if (audio != null) {
        await tts.playBytes(audio);
      } else {
        debugPrint('No TTS audio available for image response');
      }
    }
  }

  // Press-and-hold recording helpers
  Future<void> startRecordingPressed() async {
    final ok = await Permission.microphone.request().isGranted;
    if (!ok) return;
    setState(() => transcript = 'Recording...');
    await speech.startRecording();
  }

  Future<void> stopRecordingPressed() async {
    setState(() => transcript = 'Processing...');
    final path = await speech.stopRecording();
    if (path.isEmpty) {
      setState(() => transcript = 'Record failed');
      return;
    }
    final text = await hf.asr(File(path));
    setState(() => transcript = text ?? 'No transcript');
    if (text != null) {
      await askHfForText(text);
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Shahrukh Assistant - Starter',
      home: Scaffold(
        backgroundColor: Colors.black,
        appBar: AppBar(title: Text('Voice Assistant'), backgroundColor: Colors.deepPurple),
        body: Padding(
          padding: EdgeInsets.all(12),
          child: Column(
            children: [
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Transcript:', style: TextStyle(color: Colors.white70)),
                      SizedBox(height: 6),
                      Text(transcript, style: TextStyle(color: Colors.white)),
                      SizedBox(height: 14),
                      Text('Assistant:', style: TextStyle(color: Colors.white70)),
                      SizedBox(height: 6),
                      Text(assistantResponse, style: TextStyle(color: Colors.white)),
                    ],
                  ),
                ),
              ),
              Row(
                children: [
                  GestureDetector(
                    onTapDown: (_) => startRecordingPressed(),
                    onTapUp: (_) => stopRecordingPressed(),
                    onTapCancel: () => stopRecordingPressed(),
                    child: ElevatedButton(
                      onPressed: null,
                      child: Text('Hold to Record'),
                    ),
                  ),
                  SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: () async {
                      final picker = ImagePicker();
                      final picked = await picker.pickImage(source: ImageSource.gallery);
                      if (picked != null) {
                        final imageFile = File(picked.path);
                        await sendImageForVQA(imageFile, 'What is in this image?');
                      }
                    },
                    child: Text('Pick Image -> VQA'),
                  ),
                  SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: () => nativeControl.openApp('com.whatsapp'),
                    child: Text('Open WhatsApp'),
                  ),
                ],
              )
            ],
          ),
        ),
      ),
    );
  }
}
