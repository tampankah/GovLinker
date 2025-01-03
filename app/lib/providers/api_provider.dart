import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'dart:typed_data';
import 'package:http_parser/http_parser.dart';
import 'package:flutter_emoji/flutter_emoji.dart';  // Import paczki flutter_emoji

import '../models/models.dart';

class ApiProvider with ChangeNotifier {
  final List<Message> _messages = [];

  List<Message> get messages => _messages;

  Future<void> generateResponse(String question) async {
    var url = Uri.parse('https://government-assistant-api-183025368636.us-central1.run.app/generate-response');
    try {
      _addMessage(Message(message: question, isUserMessage: true));

      var response = await http.post(
        url,
        headers: {'Content-Type': 'application/json; charset=utf-8'},
        body: json.encode({'question': question}),
      );

      if (response.statusCode == 200) {
        var responseBody = utf8.decode(response.bodyBytes);
        var responseData = json.decode(responseBody);

        if (responseData is List && responseData.isNotEmpty) {
          String serverResponse = responseData[0];

          // Przetwarzanie odpowiedzi w celu zamiany tekstowych emotikonów na emoji
          serverResponse = _parseEmojis(serverResponse);

          _addMessage(Message(
            message: serverResponse,
            isUserMessage: false,
            isMarkdown: true,
          ));
        }
      } else {
        throw Exception('Failed to load response');
      }
    } catch (e) {
      _addMessage(Message(
        message: 'Error: $e',
        isUserMessage: false,
      ));
    }
  }

  Future<void> uploadDocument(Uint8List fileBytes, String fileName) async {
    var url = Uri.parse('https://government-assistant-api-183025368636.us-central1.run.app/validate-document');
    try {
      _addMessage(Message(
        message: 'Uploading document...',
        isUserMessage: true,
      ));

      // Logowanie wykrytego MIME Type
      String mimeType = _detectMimeType(fileName);
      print("Detected MIME Type: $mimeType");

      var request = http.MultipartRequest('POST', url);
      request.files.add(http.MultipartFile.fromBytes(
        'file',
        fileBytes,
        filename: fileName,
        contentType: MediaType.parse(mimeType),
      ));

      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        var responseBody = utf8.decode(response.bodyBytes);
        var responseData = json.decode(responseBody);

        String resultMessage = responseData['content'] ?? 'No content available';
        
        // Przetwarzanie odpowiedzi w celu zamiany tekstowych emotikonów na emoji
        resultMessage = _parseEmojis(resultMessage);

        _addMessage(Message(
          message: resultMessage,
          isUserMessage: false,
          isMarkdown: true,
        ));
      } else if (response.statusCode == 400) {
        var responseBody = utf8.decode(response.bodyBytes);
        var responseData = json.decode(responseBody);

        _addMessage(Message(
          message: responseData['detail'] ?? 'Unsupported file type.',
          isUserMessage: false,
        ));
      } else {
        _addMessage(Message(
          message: 'Document upload failed: ${response.reasonPhrase}',
          isUserMessage: false,
        ));
      }
    } catch (e) {
      _addMessage(Message(
        message: 'Error occurred: $e',
        isUserMessage: false,
      ));
    }
  }

  void _addMessage(Message message) {
    _messages.add(message);
    notifyListeners();
  }

  // Metoda do wykrywania typu MIME
  String _detectMimeType(String fileName) {
    if (fileName.endsWith('.pdf')) {
      return 'application/pdf';
    } else if (fileName.endsWith('.docx')) {
      return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    } else {
      // Logowanie błędu, gdy typ MIME nie jest rozpoznany
      print('Unsupported file type: $fileName');
      throw Exception('Unsupported file type. Only PDF and DOCX are allowed.');
    }
  }

  // Funkcja do parsowania tekstu na emoji
  String _parseEmojis(String message) {
    final emojiParser = EmojiParser();
    return emojiParser.emojify(message);  // Przetwarza tekst i konwertuje go na emoji
  }
}
