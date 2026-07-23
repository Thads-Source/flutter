import 'package:flutter/material.dart';

import 'auth/auth_service.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'theme.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'My App',
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ThemeMode.system,
      home: const AuthGate(),
    );
  }
}

/// Restores any saved session on launch, then shows either the login screen
/// or the home screen. Sessions persist across app restarts.
class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  final AuthService _auth = AuthService();
  String? _email;
  bool _restoring = true;

  @override
  void initState() {
    super.initState();
    _restoreSession();
  }

  Future<void> _restoreSession() async {
    final String? email = await _auth.currentUserEmail();
    if (!mounted) {
      return;
    }
    setState(() {
      _email = email;
      _restoring = false;
    });
  }

  Future<void> _signOut() async {
    await _auth.signOut();
    if (!mounted) {
      return;
    }
    setState(() => _email = null);
  }

  @override
  Widget build(BuildContext context) {
    if (_restoring) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }
    if (_email == null) {
      return LoginScreen(
        auth: _auth,
        onSignedIn: (String email) => setState(() => _email = email),
      );
    }
    return HomeScreen(userEmail: _email!, onSignOut: _signOut);
  }
}
