// models.dart
class Message {
  final String message;
  final bool isUserMessage;
  final bool isMarkdown;

  Message({
    required this.message,
    required this.isUserMessage,
    this.isMarkdown = false,
  });
}
