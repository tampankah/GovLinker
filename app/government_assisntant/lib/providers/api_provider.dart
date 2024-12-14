import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiProvider with ChangeNotifier {
  List<Message> _messages = [];

  List<Message> get messages => _messages;

  Future<void> generateResponse(String question) async {
    var url = Uri.parse('http://127.0.0.1:8000/generate-response');
    try {
      _messages.add(Message(message: question, isUserMessage: true));
      notifyListeners();

      var response = await http.post(
        url,
        headers: {'Content-Type': 'application/json; charset=utf-8'},
        body: json.encode({'question': question}),
      );

      if (response.statusCode == 200) {
        var responseBody = utf8.decode(response.bodyBytes); // Decode response as UTF-8
        var responseData = json.decode(responseBody);

        if (responseData is List) {
          String serverResponse = responseData.isNotEmpty ? responseData[0] : '';
          _messages.add(Message(message: serverResponse, isUserMessage: false, isMarkdown: true));
        }

        notifyListeners();
      } else {
        throw Exception('Failed to load response');
      }
    } catch (e) {
      print('Error occurred: $e');
      throw Exception('Failed to send request');
    }
  }
}

class Message {
  final String message;
  final bool isUserMessage;
  final bool isMarkdown;

  Message({required this.message, required this.isUserMessage, this.isMarkdown = false});
}
