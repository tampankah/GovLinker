import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:html2md/html2md.dart' as html2md; // For converting HTML to Markdown

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

  // Function to open links
  Future<void> _openLink(String url) async {
    final Uri uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else {
      throw 'Could not launch $url';
    }
  }

  // Convert HTML to Markdown
  String _convertHtmlToMarkdown(String html) {
    return html2md.convert(html); // Uses html2md to convert HTML to Markdown
  }

  @override
  Widget build(BuildContext context) {
    // If message is Markdown, render it as Markdown, otherwise convert HTML to Markdown
    final String renderedMessage = isMarkdown ? message : _convertHtmlToMarkdown(message);

    return Align(
      alignment: isUserMessage ? Alignment.centerRight : Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.all(8.0),
        child: Container(
          decoration: BoxDecoration(
            color: isUserMessage ? Colors.black : Colors.grey[800], // Black for user, grey for response
            borderRadius: BorderRadius.circular(12),
            border: isUserMessage
                ? Border.all(color: Colors.deepPurple, width: 2) // Purple border for user message
                : null, // No border for response
          ),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: MarkdownBody(
            data: renderedMessage,
            styleSheet: MarkdownStyleSheet.fromTheme(Theme.of(context)).copyWith(
              p: TextStyle(
                color: Colors.white, // White text for both user and response
                fontWeight: isUserMessage ? FontWeight.normal : FontWeight.bold,
              ),
              listBullet: const TextStyle(color: Colors.white),
            ),
            onTapLink: (text, href, title) {
              if (href != null) {
                _openLink(href);
              }
            },
          ),
        ),
      ),
    );
  }
}
