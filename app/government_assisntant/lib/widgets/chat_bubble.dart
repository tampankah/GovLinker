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
    final String renderedMessage = isMarkdown ? message : _convertHtmlToMarkdown(message);

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
          child: MarkdownBody(
            data: renderedMessage,
            styleSheet: MarkdownStyleSheet.fromTheme(Theme.of(context)).copyWith(
              p: const TextStyle(color: Colors.white),
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
