import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Who can do what in the app.
enum UserRole { kitchen, manager, owner }

extension UserRoleLabel on UserRole {
  String get label => switch (this) {
        UserRole.kitchen => 'Kitchen',
        UserRole.manager => 'Manager',
        UserRole.owner => 'Owner',
      };

  /// Kitchen staff update counts; managers and owners can also add, edit,
  /// and delete items and see the overview/shopping list.
  bool get canManageItems => this != UserRole.kitchen;
}

/// The signed-in user.
class AppUser {
  const AppUser({required this.email, required this.role});

  final String email;
  final UserRole role;
}

/// Outcome of a sign-in or sign-up attempt. When [ok] is false, [message]
/// holds a friendly explanation suitable for showing directly in the UI.
class AuthResult {
  const AuthResult.ok()
      : ok = true,
        message = '';

  const AuthResult.error(this.message) : ok = false;

  final bool ok;
  final String message;
}

/// Device-local authentication.
///
/// Accounts live in local storage on this device only. Passwords are never
/// stored: each account keeps a random salt and a SHA-256 hash, and sign-in
/// re-hashes the entered password and compares. This is honest security for
/// a single-device app; for accounts that work across devices, swap this
/// class for a backed service (e.g. Firebase Auth) — the rest of the app
/// only talks to this interface. Note that in a hosted setup, roles should
/// be assigned by the owner/manager server-side, not chosen at sign-up.
class AuthService {
  static const String _usersKey = 'auth_users';
  static const String _sessionKey = 'auth_session_email';

  /// The signed-in user, or null when signed out. Sessions survive app
  /// restarts.
  Future<AppUser?> currentUser() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    final String? email = prefs.getString(_sessionKey);
    if (email == null) {
      return null;
    }
    final Map<String, dynamic> users = _loadUsers(prefs);
    final dynamic record = users[email];
    if (record == null) {
      return null;
    }
    final UserRole role = UserRole.values.firstWhere(
      (UserRole r) => r.name == record['role'],
      orElse: () => UserRole.kitchen,
    );
    return AppUser(email: email, role: role);
  }

  Future<AuthResult> signUp(
    String email,
    String password,
    UserRole role,
  ) async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    final Map<String, dynamic> users = _loadUsers(prefs);
    final String key = email.trim().toLowerCase();
    if (users.containsKey(key)) {
      return const AuthResult.error(
        'An account with that email already exists. Try signing in instead.',
      );
    }
    final String salt = _newSalt();
    users[key] = <String, String>{
      'salt': salt,
      'hash': _hash(salt, password),
      'role': role.name,
    };
    await prefs.setString(_usersKey, jsonEncode(users));
    await prefs.setString(_sessionKey, key);
    return const AuthResult.ok();
  }

  Future<AuthResult> signIn(String email, String password) async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    final Map<String, dynamic> users = _loadUsers(prefs);
    final String key = email.trim().toLowerCase();
    final dynamic record = users[key];
    if (record == null) {
      return const AuthResult.error(
        'No account found for that email. Create one below.',
      );
    }
    final String salt = record['salt'] as String;
    final String storedHash = record['hash'] as String;
    if (_hash(salt, password) != storedHash) {
      return const AuthResult.error("That password doesn't match. Try again.");
    }
    await prefs.setString(_sessionKey, key);
    return const AuthResult.ok();
  }

  Future<void> signOut() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.remove(_sessionKey);
  }

  Map<String, dynamic> _loadUsers(SharedPreferences prefs) {
    final String raw = prefs.getString(_usersKey) ?? '{}';
    return jsonDecode(raw) as Map<String, dynamic>;
  }

  String _newSalt() {
    final Random random = Random.secure();
    final List<int> bytes =
        List<int>.generate(16, (_) => random.nextInt(256));
    return base64Encode(bytes);
  }

  String _hash(String salt, String password) {
    return sha256.convert(utf8.encode('$salt:$password')).toString();
  }
}
