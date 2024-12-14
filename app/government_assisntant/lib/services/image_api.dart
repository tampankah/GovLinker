import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class ApiService {
  final String baseUrl;

  ApiService({required this.baseUrl});

  // Endpoint to process images
  Future<Map<String, dynamic>> processImage({
    required File imageFile,
  }) async {
    var uri = Uri.parse('$baseUrl/processing-image');
    var request = http.MultipartRequest('POST', uri);

    // Adding image file to request
    request.files.add(await http.MultipartFile.fromPath(
      'file',
      imageFile.path,
      filename: imageFile.path.split('/').last,
    ));

    // Send the request and handle response
    var streamedResponse = await request.send();
    var response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      return json.decode(response.body); // Return the response body as a map
    } else {
      throw Exception('Failed to process image: ${response.body}');
    }
  }
}
