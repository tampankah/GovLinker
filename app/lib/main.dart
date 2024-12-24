import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/api_provider.dart';
import 'pages/chat_page.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider<ApiProvider>(
      create: (_) => ApiProvider(),
      child: MaterialApp(
        title: 'Government Assistant',
        theme: ThemeData(
          scaffoldBackgroundColor: Colors.black, // Black background for the whole app
          appBarTheme: const AppBarTheme(
            backgroundColor: Colors.deepPurple, // Purple app bar color
          ),
          textTheme: const TextTheme(
            bodyLarge: TextStyle(color: Colors.white), // White text color for the body
          ),
          colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
          useMaterial3: true,
        ),
        home: const ChatPage(),
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}
