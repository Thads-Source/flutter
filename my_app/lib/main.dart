import 'package:flutter/material.dart';

import 'auth/auth_service.dart';
import 'screens/inventory_home_screen.dart';
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
      title: 'Kitchen Inventory',
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ThemeMode.system,
      home: const AuthGate(),
    );
  }
}

/// Restores any saved session on launch, then shows either the login screen
/// or the inventory. Sessions persist across app restarts.
class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  final AuthService _auth = AuthService();
  AppUser? _user;
  bool _restoring = true;

  @override
  void initState() {
    super.initState();
    _restoreSession();
  }

  Future<void> _restoreSession() async {
    final AppUser? user = await _auth.currentUser();
    if (!mounted) {
      return;
    }
    setState(() {
      _user = user;
      _restoring = false;
    });
  }

  Future<void> _signOut() async {
    await _auth.signOut();
    if (!mounted) {
      return;
    }
    setState(() => _user = null);
  }

  @override
  Widget build(BuildContext context) {
    if (_restoring) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }
    final AppUser? user = _user;
    if (user == null) {
      return LoginScreen(auth: _auth, onSignedIn: _restoreSession);
    }
    return InventoryHomeScreen(user: user, onSignOut: _signOut);
  }
}
