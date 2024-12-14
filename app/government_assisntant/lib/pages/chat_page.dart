import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/api_provider.dart';
import '../widgets/chat_bubble.dart';

class ChatPage extends StatelessWidget {
  const ChatPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Government Assistant'),
        backgroundColor: Colors.black,
        centerTitle: true,
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

  // Function to send the message
  void _sendMessage() async {
    if (_controller.text.trim().isEmpty) return;

    final apiProvider = Provider.of<ApiProvider>(context, listen: false);  // Accessing ApiProvider
    await apiProvider.generateResponse(_controller.text);  // Sending request to API

    _controller.clear();
  }

  @override
  Widget build(BuildContext context) {
    final apiProvider = Provider.of<ApiProvider>(context);  // Accessing ApiProvider

    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            itemCount: apiProvider.answers.length,  // Fetching answers from ApiProvider
            itemBuilder: (context, index) {
              final message = apiProvider.answers[index];  // API response
              final isUserMessage = index.isOdd;  // Change to 'isOdd' for alternating sides
              return ChatBubble(
                message: message,
                isUserMessage: isUserMessage,
              );
            },
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(8.0),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _controller,
                  style: const TextStyle(color: Colors.white), // White text color for input
                  decoration: const InputDecoration(
                    hintText: 'Type your message...',
                    hintStyle: TextStyle(color: Colors.white), // White hint text
                    border: OutlineInputBorder(),
                    filled: true,
                    fillColor: Colors.black, // Black background for input field
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
