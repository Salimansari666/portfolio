import 'package:flutter/foundation.dart';

class NativeControl {
  /// Stub to open a native app by id/package name. Replace with platform
  /// specific code (MethodChannel, platform intent, etc.).
  void openApp(String appId) {
    // For now, just log — real implementation should call platform APIs.
    debugPrint('NativeControl.openApp: $appId');
  }
}
