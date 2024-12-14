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

  // Method to send the question to the API
  Future<void> generateResponse(String question) async {
    var url = Uri.parse('http://127.0.0.1:8000/generate-response');  // Change localhost to 127.0.0.1 if needed
    try {
      var response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'question': question,
        }),
      );

      // Debugging output
      print('Response Status: ${response.statusCode}');
      print('Response Body: ${response.body}');

      if (response.statusCode == 200) {
        var responseData = json.decode(response.body);

        // Ensure you're receiving a list of strings
        if (responseData is List) {
          _answers = List<String>.from(responseData); // Expecting a list of strings
        } else {
          print("Unexpected response format");
        }

        notifyListeners();
      }
    } catch (e) {
      // Handle any errors (e.g., network issues)
      print('Error occurred: $e');
      throw Exception('Failed to send request');
    }
  }

  // Method to validate a document
  Future<void> validateDocument(List<int> fileBytes) async {
    var url = Uri.parse('http://127.0.0.1:8000/validate-document');  // Ensure this endpoint is correct
    try {
      var request = http.MultipartRequest('POST', url)
        ..files.add(http.MultipartFile.fromBytes('file', fileBytes, filename: 'document.pdf'));

      var response = await request.send();

      // Debugging output
      print('Response Status: ${response.statusCode}');

      if (response.statusCode == 200) {
        var responseBody = await response.stream.bytesToString();
        var data = json.decode(responseBody);
        _isValid = data['isValid'];
        _missingFields = List<String>.from(data['missingFields']);
        _errors = List<String>.from(data['errors']);
        notifyListeners();
      } else {
        print('Error: ${response.statusCode}');
        throw Exception('Failed to validate document');
      }
    } catch (e) {
      // Handle any errors (e.g., network issues)
      print('Error occurred: $e');
      throw Exception('Failed to send request');
    }
  }
}
