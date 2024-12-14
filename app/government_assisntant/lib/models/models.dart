import 'dart:convert';

class QuestionRequest {
  final String question;

  QuestionRequest({required this.question});

  // Konwersja z obiektu do JSON
  Map<String, dynamic> toJson() {
    return {
      'question': question,
    };
  }

  // Konwersja z JSON do obiektu
  factory QuestionRequest.fromJson(Map<String, dynamic> json) {
    return QuestionRequest(
      question: json['question'],
    );
  }
}

class DocumentCheckResult {
  final bool isValid;
  final List<String> missingFields;
  final List<String> errors;

  DocumentCheckResult({
    required this.isValid,
    required this.missingFields,
    required this.errors,
  });

  // Konwersja z obiektu do JSON
  Map<String, dynamic> toJson() {
    return {
      'isValid': isValid,
      'missingFields': missingFields,
      'errors': errors,
    };
  }

  // Konwersja z JSON do obiektu
  factory DocumentCheckResult.fromJson(Map<String, dynamic> json) {
    return DocumentCheckResult(
      isValid: json['isValid'],
      missingFields: List<String>.from(json['missingFields']),
      errors: List<String>.from(json['errors']),
    );
  }
}

class GenerateResponse {
  final List<String> answers;

  GenerateResponse({required this.answers});

  // Konwersja z obiektu do JSON
  Map<String, dynamic> toJson() {
    return {
      'answers': answers,
    };
  }

  // Konwersja z JSON do obiektu
  factory GenerateResponse.fromJson(Map<String, dynamic> json) {
    return GenerateResponse(
      answers: List<String>.from(json['answers']),
    );
  }
}
