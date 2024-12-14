import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiProvider with ChangeNotifier {
  List<Message> _messages = [];  // Lista wiadomości, która będzie zawierać zarówno zapytania, jak i odpowiedzi

  List<Message> get messages => _messages;  // Getter dla listy wiadomości

  // Method to send the question to the API
  Future<void> generateResponse(String question) async {
    var url = Uri.parse('http://127.0.0.1:8000/generate-response');
    try {
      // Dodanie wiadomości użytkownika do listy
      _messages.add(Message(message: question, isUserMessage: true));
      notifyListeners();

      var response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'question': question}),
      );

      print('Response Status: ${response.statusCode}');
      print('Response Body: ${response.body}');

      if (response.statusCode == 200) {
        var responseData = json.decode(response.body);

        // Zabezpieczenie przed błędami typu
        if (responseData is List) {
          String serverResponse = responseData.isNotEmpty ? responseData[0] : '';
          _messages.add(Message(message: serverResponse, isUserMessage: false));  // Dodanie odpowiedzi serwera
        } else {
          print("Unexpected response format");
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

// Klasa do reprezentowania wiadomości
class Message {
  final String message;
  final bool isUserMessage;

  Message({required this.message, required this.isUserMessage});
}
