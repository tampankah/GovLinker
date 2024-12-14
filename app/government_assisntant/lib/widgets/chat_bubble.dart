import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

class ChatBubble extends StatelessWidget {
  final String message;
  final bool isUserMessage;
  final bool isMarkdown;

  const ChatBubble({
    Key? key,
    required this.message,
    required this.isUserMessage,
    this.isMarkdown = false,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isUserMessage ? Alignment.centerRight : Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.all(8.0),
        child: Container(
          decoration: BoxDecoration(
            color: isUserMessage ? Colors.blue : Colors.grey[700],
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.deepPurple, width: 2),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: isMarkdown
              ? MarkdownBody(
            data: message,
            styleSheet: MarkdownStyleSheet.fromTheme(Theme.of(context)).copyWith(
              p: const TextStyle(color: Colors.white),
              listBullet: const TextStyle(color: Colors.white),
            ),
          )
              : Text(
            message,
            style: const TextStyle(color: Colors.white),
          ),
        ),
      ),
    );
  }
}
