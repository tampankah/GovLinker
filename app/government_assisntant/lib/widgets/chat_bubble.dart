import 'package:flutter/material.dart';

class ChatBubble extends StatelessWidget {
  final String message;
  final bool isUserMessage;

  const ChatBubble({
    Key? key,
    required this.message,
    required this.isUserMessage,
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
            border: Border.all(color: Colors.deepPurple, width: 2), // Purple border
          ),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Text(
            message,
            style: const TextStyle(color: Colors.white), // White text color
          ),
        ),
      ),
    );
  }
}
