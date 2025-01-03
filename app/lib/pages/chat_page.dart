import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/api_provider.dart';
import '../widgets/chat_bubble.dart';
import 'package:file_picker/file_picker.dart';
import 'dart:typed_data'; 

class ChatPage extends StatelessWidget {
  const ChatPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: ShaderMask(
          blendMode: BlendMode.srcIn,
          shaderCallback: (bounds) => LinearGradient(
            colors: [Colors.black, Colors.black], // Black interior
          ).createShader(bounds),
          child: Stack(
            children: [
              // Outline layer
              Text(
                'Govgiggler',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.5,
                  foreground: Paint()
                    ..style = PaintingStyle.stroke
                    ..strokeWidth = 2
                    ..color = Colors.white, // White outline
                ),
              ),
              // Filled text layer
              Text(
                'Govgiggler',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.5,
                  color: Colors.black, // Black interior
                ),
              ),
            ],
          ),
        ),
        backgroundColor: Colors.grey[800],
        centerTitle: true,
        elevation: 0,
      ),
      body: const ChatBody(),
    );
  }
}

class ChatBody extends StatefulWidget {
  const ChatBody({super.key});

  @override
  State<ChatBody> createState() => _ChatBodyState();
}

class _ChatBodyState extends State<ChatBody> {
  final TextEditingController _controller = TextEditingController();

  void _sendMessage() async {
    if (_controller.text.trim().isEmpty) return;

    final apiProvider = Provider.of<ApiProvider>(context, listen: false);
    await apiProvider.generateResponse(_controller.text);

    _controller.clear();
  }

  void _addDocument() async {
    final apiProvider = Provider.of<ApiProvider>(context, listen: false);

    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'doc', 'docx'],
      );

      if (result != null) {
        Uint8List? fileBytes = result.files.single.bytes;
        String fileName = result.files.single.name;
        await apiProvider.uploadDocument(fileBytes!, fileName);
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to pick or upload document: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final apiProvider = Provider.of<ApiProvider>(context);

    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            itemCount: apiProvider.messages.length,
            itemBuilder: (context, index) {
              final message = apiProvider.messages[index];
              return ChatBubble(
                message: message.message,
                isUserMessage: message.isUserMessage,
                isMarkdown: message.isMarkdown,
              );
            },
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(8.0),
          child: Row(
            children: [
              IconButton(
                icon: const Icon(Icons.attach_file, color: Colors.white),
                onPressed: _addDocument,
              ),
              Expanded(
                child: TextField(
                  controller: _controller,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    hintText: 'Type your message...',
                    hintStyle: TextStyle(color: Colors.white),
                    border: OutlineInputBorder(),
                    filled: true,
                    fillColor: Colors.black,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.send, color: Colors.white),
                onPressed: _sendMessage,
              ),
            ],
          ),
        ),
      ],
    );
  }
}
