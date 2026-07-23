import 'package:flutter/material.dart';

/// Home screen: a simple task list that demonstrates the app's two design
/// goals — readable text and large, forgiving tap targets.
class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    required this.userEmail,
    required this.onSignOut,
  });

  final String userEmail;
  final VoidCallback onSignOut;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _Task {
  _Task(this.label);

  final String label;
  bool done = false;
}

class _HomeScreenState extends State<HomeScreen> {
  final List<_Task> _tasks = <_Task>[
    _Task('Tap a card to mark it done'),
    _Task('Notice every target is thumb-sized'),
    _Task('Try dark mode — contrast holds up'),
  ];

  int _nextTaskNumber = 1;

  void _addTask() {
    setState(() {
      _tasks.add(_Task('New task ${_nextTaskNumber++}'));
    });
  }

  void _toggle(_Task task) {
    setState(() {
      task.done = !task.done;
    });
  }

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    final TextTheme text = Theme.of(context).textTheme;
    final int remaining = _tasks.where((_Task t) => !t.done).length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Today'),
        actions: <Widget>[
          IconButton(
            tooltip: 'Sign out',
            icon: const Icon(Icons.logout),
            onPressed: widget.onSignOut,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 96),
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Text(
              remaining == 0
                  ? 'All done. Nice work!'
                  : '$remaining thing${remaining == 1 ? '' : 's'} left to do',
              style: text.headlineMedium,
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: Text(
              'Signed in as ${widget.userEmail}',
              style: text.bodyMedium!.copyWith(color: scheme.onSurfaceVariant),
            ),
          ),
          for (final _Task task in _tasks)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _TaskCard(
                task: task,
                onTap: () => _toggle(task),
              ),
            ),
          if (_tasks.isEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 40),
              child: Text(
                'Nothing here yet.\nAdd your first task below.',
                textAlign: TextAlign.center,
                style: text.bodyLarge!.copyWith(
                  color: scheme.onSurfaceVariant,
                ),
              ),
            ),
        ],
      ),
      // Bottom-anchored primary action: the easiest place for a thumb to
      // reach on a phone held one-handed.
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
      floatingActionButton: FilledButton.icon(
        onPressed: _addTask,
        icon: const Icon(Icons.add),
        label: const Text('Add task'),
      ),
    );
  }
}

class _TaskCard extends StatelessWidget {
  const _TaskCard({required this.task, required this.onTap});

  final _Task task;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    final TextTheme text = Theme.of(context).textTheme;

    // The whole card is one big tap target (well past the 48px minimum),
    // so users don't have to aim for the checkbox itself.
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
          child: Row(
            children: <Widget>[
              Icon(
                task.done
                    ? Icons.check_circle
                    : Icons.radio_button_unchecked,
                size: 28,
                color: task.done ? scheme.primary : scheme.onSurfaceVariant,
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  task.label,
                  style: text.bodyLarge!.copyWith(
                    decoration:
                        task.done ? TextDecoration.lineThrough : null,
                    color: task.done
                        ? scheme.onSurfaceVariant
                        : scheme.onSurface,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
