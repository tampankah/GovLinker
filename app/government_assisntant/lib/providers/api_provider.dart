import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiProvider with ChangeNotifier {
  List<String> _answers = [];
  bool _isValid = false;
  List<String> _missingFields = [];
  List<String> _errors = [];

  List<String> get answers => _answers;
  bool get isValid => _isValid;
  List<String> get missingFields => _missingFields;
  List<String> get errors => _errors;

  // Metoda wysyłająca zapytanie do API
  Future<void> generateResponse(String question) async {
    var url = Uri.parse('http://your-api-url.com/generate-response');  // Zmień na odpowiedni URL API
    var response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'question': question}),
    );

    if (response.statusCode == 200) {
      var responseData = json.decode(response.body);
      _answers = List<String>.from(responseData['answers']);
      notifyListeners();
    } else {
      throw Exception('Failed to load response');
    }
  }

  // Metoda do walidacji dokumentu
  Future<void> validateDocument(List<int> fileBytes) async {
    var url = Uri.parse('http://your-api-url.com/validate-document');  // Zmień na odpowiedni URL API
    var request = http.MultipartRequest('POST', url)
      ..files.add(http.MultipartFile.fromBytes('file', fileBytes, filename: 'document.pdf'));

    var response = await request.send();

    if (response.statusCode == 200) {
      var responseBody = await response.stream.bytesToString();
      var data = json.decode(responseBody);
      _isValid = data['isValid'];
      _missingFields = List<String>.from(data['missingFields']);
      _errors = List<String>.from(data['errors']);
      notifyListeners();
    } else {
      throw Exception('Failed to validate document');
    }
  }
}
