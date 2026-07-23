// Copyright 2014 The Flutter Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

import 'package:flutter/material.dart';

import '../auth/auth_service.dart';

/// Sign-in / create-account screen. One form serves both modes; a text
/// button at the bottom flips between them. Follows the app's ergonomics
/// rules: 48px+ targets, 16px+ text, inline validation, and errors written
/// in plain language.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.auth, required this.onSignedIn});

  final AuthService auth;
  final VoidCallback onSignedIn;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _email = TextEditingController();
  final TextEditingController _password = TextEditingController();

  bool _creatingAccount = false;
  bool _obscurePassword = true;
  bool _busy = false;
  UserRole _role = UserRole.manager;
  String? _errorMessage;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    setState(() {
      _busy = true;
      _errorMessage = null;
    });
    final String email = _email.text.trim();
    final AuthResult result = _creatingAccount
        ? await widget.auth.signUp(email, _password.text, _role)
        : await widget.auth.signIn(email, _password.text);
    if (!mounted) {
      return;
    }
    if (result.ok) {
      widget.onSignedIn();
    } else {
      setState(() {
        _busy = false;
        _errorMessage = result.message;
      });
    }
  }

  void _toggleMode() {
    setState(() {
      _creatingAccount = !_creatingAccount;
      _errorMessage = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    final TextTheme text = Theme.of(context).textTheme;

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    Text(
                      _creatingAccount ? 'Create your account' : 'Welcome back',
                      style: text.headlineMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _creatingAccount
                          ? "One quick step and you're in."
                          : 'Sign in to see your inventory.',
                      style: text.bodyMedium!.copyWith(
                        color: scheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 28),
                    TextFormField(
                      key: const Key('email-field'),
                      controller: _email,
                      keyboardType: TextInputType.emailAddress,
                      autofillHints: const <String>[AutofillHints.email],
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(
                        labelText: 'Email',
                        border: OutlineInputBorder(),
                      ),
                      validator: (String? value) {
                        final String v = value?.trim() ?? '';
                        if (v.isEmpty || !v.contains('@') || !v.contains('.')) {
                          return 'Enter a valid email address.';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      key: const Key('password-field'),
                      controller: _password,
                      obscureText: _obscurePassword,
                      autofillHints: const <String>[AutofillHints.password],
                      textInputAction: TextInputAction.done,
                      onFieldSubmitted: (_) => _submit(),
                      decoration: InputDecoration(
                        labelText: 'Password',
                        border: const OutlineInputBorder(),
                        suffixIcon: IconButton(
                          tooltip: _obscurePassword
                              ? 'Show password'
                              : 'Hide password',
                          icon: Icon(
                            _obscurePassword
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                          ),
                          onPressed: () => setState(
                            () => _obscurePassword = !_obscurePassword,
                          ),
                        ),
                      ),
                      validator: (String? value) {
                        if ((value ?? '').length < 8) {
                          return 'Use at least 8 characters.';
                        }
                        return null;
                      },
                    ),
                    if (_creatingAccount) ...<Widget>[
                      const SizedBox(height: 20),
                      Text('Your role', style: text.titleMedium),
                      const SizedBox(height: 8),
                      SegmentedButton<UserRole>(
                        segments: const <ButtonSegment<UserRole>>[
                          ButtonSegment<UserRole>(
                            value: UserRole.manager,
                            label: Text('Manager'),
                          ),
                          ButtonSegment<UserRole>(
                            value: UserRole.owner,
                            label: Text('Owner'),
                          ),
                        ],
                        selected: <UserRole>{_role},
                        onSelectionChanged: (Set<UserRole> selection) =>
                            setState(() => _role = selection.first),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Only 4 accounts can exist: 3 managers and 1 owner.',
                        style: text.bodyMedium!.copyWith(
                          color: scheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                    if (_errorMessage != null)
                      Container(
                        margin: const EdgeInsets.only(top: 16),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 12,
                        ),
                        decoration: BoxDecoration(
                          color: scheme.errorContainer,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          _errorMessage!,
                          style: text.bodyMedium!.copyWith(
                            color: scheme.onErrorContainer,
                          ),
                        ),
                      ),
                    const SizedBox(height: 24),
                    FilledButton(
                      onPressed: _busy ? null : _submit,
                      child: _busy
                          ? const SizedBox(
                              height: 22,
                              width: 22,
                              child: CircularProgressIndicator(strokeWidth: 2.5),
                            )
                          : Text(
                              _creatingAccount ? 'Create account' : 'Sign in',
                            ),
                    ),
                    const SizedBox(height: 12),
                    TextButton(
                      onPressed: _busy ? null : _toggleMode,
                      child: Text(
                        _creatingAccount
                            ? 'Already have an account? Sign in here'
                            : 'New here? Create an account',
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
