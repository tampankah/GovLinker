import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'dart:io';
import 'package:http_parser/http_parser.dart';

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
          String serverResponse = responseData.isNotEmpty
              ? responseData[0]
              : '';
          _messages.add(Message(
              message: serverResponse, isUserMessage: false, isMarkdown: true));
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

  Future<void> uploadDocument(String filePath) async {
    var url = Uri.parse('http://127.0.0.1:8000/validate-document'); // Updated endpoint
    try {
      // Inform the user about the upload
      _messages.add(Message(message: 'Uploading document...', isUserMessage: true));
      notifyListeners();

      // Detect the file's MIME type
      String mimeType = '';
      if (filePath.endsWith('.pdf')) {
        mimeType = 'application/pdf';
      } else if (filePath.endsWith('.docx')) {
        mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
      } else {
        throw Exception('Unsupported file type. Only PDF and DOCX are allowed.');
      }

      // Create a multipart request with correct headers
      var request = http.MultipartRequest('POST', url);
      request.files.add(await http.MultipartFile.fromPath(
        'file',
        filePath,
        contentType: MediaType.parse(mimeType),
      ));

      // Send the request and wait for the response
      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        // Decode the response and display the result
        var responseBody = utf8.decode(response.bodyBytes);
        var responseData = json.decode(responseBody);

        // Assuming the response contains a 'content' key with the full document validation message
        String resultMessage = responseData['content'] ?? 'No content available';

        // Add the result message to the chat
        _messages.add(Message(
          message: resultMessage,
          isUserMessage: false,
          isMarkdown: true, // Mark as markdown to render properly
        ));
      } else if (response.statusCode == 400) {
        // Handle unsupported file type error
        var responseBody = utf8.decode(response.bodyBytes);
        var responseData = json.decode(responseBody);

        _messages.add(Message(
          message: responseData['detail'] ?? 'Unsupported file type.',
          isUserMessage: false,
        ));
      } else {
        // Handle other errors
        _messages.add(Message(
          message: 'Document upload failed: ${response.reasonPhrase}',
          isUserMessage: false,
        ));
      }

      notifyListeners();
    } catch (e) {
      // Handle unexpected errors
      print('Error occurred: $e');
      _messages.add(Message(
        message: e.toString(),
        isUserMessage: false,
      ));
      notifyListeners();
    }
  }
}

class Message {
  final String message;
  final bool isUserMessage;
  final bool isMarkdown;

  Message({required this.message, required this.isUserMessage, this.isMarkdown = false});
}
