import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class ChatProvider extends ChangeNotifier {
  List<String> _messages = [];
  String _response = '';

  List<String> get messages => _messages;
  String get response => _response;

  // Metoda do wysyłania zapytania do API
  Future<void> sendMessage(String message) async {
    final url = Uri.parse('http://localhost:8080/generate-response');
    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'message': message}),
      );
      if (response.statusCode == 200) {
        _response = json.decode(response.body)['response'];
        _messages.add(message); // Dodaj wiadomość użytkownika
        _messages.add(_response); // Dodaj odpowiedź z API
      } else {
        _messages.add('Error: Unable to fetch response');
      }
      notifyListeners();
    } catch (e) {
      _messages.add('Error: $e');
      notifyListeners();
    }
  }
}
