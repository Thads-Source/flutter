import 'dart:math';

import 'package:flutter/material.dart';

import '../auth/auth_service.dart';
import '../inventory/inventory_store.dart';
import '../models/history_entry.dart';
import '../models/inventory_item.dart';

enum _Tab { inventory, overview, history }

/// The main screen after signing in.
///
/// Only managers and the owner have accounts, so everyone gets full
/// access: the inventory list with count steppers, add/edit/delete via a
/// bottom sheet, an Overview tab (stock stats plus a shopping list of
/// everything running low), and the History tab of all changes.
class InventoryHomeScreen extends StatefulWidget {
  const InventoryHomeScreen({
    super.key,
    required this.user,
    required this.onSignOut,
  });

  final AppUser user;
  final VoidCallback onSignOut;

  @override
  State<InventoryHomeScreen> createState() => _InventoryHomeScreenState();
}

class _InventoryHomeScreenState extends State<InventoryHomeScreen> {
  final InventoryStore _store = InventoryStore();
  List<InventoryItem>? _items;
  List<HistoryEntry>? _history;
  int _tabIndex = 0;

  static const List<_Tab> _tabs = <_Tab>[
    _Tab.inventory,
    _Tab.overview,
    _Tab.history,
  ];

  _Tab get _currentTab => _tabs[_tabIndex];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final List<InventoryItem> items = await _store.load();
    final List<HistoryEntry> history = await _store.loadHistory();
    if (!mounted) {
      return;
    }
    setState(() {
      _items = items;
      _history = history;
    });
  }

  /// Records one line of history (newest first) and persists it.
  Future<void> _log(String message) async {
    setState(() {
      _history!.insert(
        0,
        HistoryEntry(
          at: DateTime.now(),
          by: widget.user.email,
          message: message,
        ),
      );
      if (_history!.length > InventoryStore.maxHistoryEntries) {
        _history!.removeRange(
          InventoryStore.maxHistoryEntries,
          _history!.length,
        );
      }
    });
    await _store.saveHistory(_history!);
  }

  Future<void> _adjustCount(InventoryItem item, double delta) async {
    final double before = item.quantity;
    final double after = max(0, before + delta);
    if (after == before) {
      return;
    }
    await _apply(() {
      item.quantity = after;
      item.lastCountedBy = widget.user.email;
      item.lastCountedAt = DateTime.now();
    });
    await _log(
      '${item.name}: count ${formatQuantity(before)} → '
      '${formatQuantity(after)}',
    );
  }

  /// Applies a change to the item list, refreshes the UI, and persists.
  Future<void> _apply(VoidCallback change) async {
    setState(change);
    await _store.save(_items!);
  }

  Future<void> _openItemSheet({InventoryItem? item}) async {
    final _ItemSheetResult? result = await showModalBottomSheet<_ItemSheetResult>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _ItemSheet(item: item),
    );
    if (result == null) {
      return;
    }
    if (result.delete) {
      await _apply(
        () => _items!.removeWhere((InventoryItem i) => i.id == item!.id),
      );
      await _log('Removed ${item!.name}');
      return;
    }
    final InventoryItem updated = result.item!;
    if (item == null) {
      updated.lastCountedBy = widget.user.email;
      updated.lastCountedAt = DateTime.now();
      await _apply(() => _items!.add(updated));
      await _log(
        'Added ${updated.name} '
        '(${formatQuantity(updated.quantity)} ${updated.unit})',
      );
      return;
    }
    final bool countChanged = updated.quantity != item.quantity;
    final bool detailsChanged = updated.name != item.name ||
        updated.category != item.category ||
        updated.unit != item.unit ||
        updated.par != item.par;
    if (countChanged) {
      updated.lastCountedBy = widget.user.email;
      updated.lastCountedAt = DateTime.now();
    }
    await _apply(() {
      final int index =
          _items!.indexWhere((InventoryItem i) => i.id == item.id);
      _items![index] = updated;
    });
    if (countChanged) {
      await _log(
        '${updated.name}: count ${formatQuantity(item.quantity)} → '
        '${formatQuantity(updated.quantity)}',
      );
    }
    if (detailsChanged) {
      await _log('Updated ${updated.name} details');
    }
  }

  @override
  Widget build(BuildContext context) {
    final List<InventoryItem>? items = _items;
    final List<HistoryEntry>? history = _history;
    if (items == null || history == null) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    final String title = switch (_currentTab) {
      _Tab.inventory => 'Inventory',
      _Tab.overview => 'Overview',
      _Tab.history => 'History',
    };
    final Widget body = switch (_currentTab) {
      _Tab.inventory => _InventoryList(
          items: items,
          user: widget.user,
          onAdjust: _adjustCount,
          onOpen: (InventoryItem item) => _openItemSheet(item: item),
        ),
      _Tab.overview => _OverviewTab(items: items),
      _Tab.history => _HistoryTab(entries: history),
    };

    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        actions: <Widget>[
          IconButton(
            tooltip: 'Sign out',
            icon: const Icon(Icons.logout),
            onPressed: widget.onSignOut,
          ),
        ],
      ),
      body: body,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tabIndex,
        onDestinationSelected: (int index) =>
            setState(() => _tabIndex = index),
        destinations: <NavigationDestination>[
          for (final _Tab tab in _tabs)
            switch (tab) {
              _Tab.inventory => const NavigationDestination(
                  icon: Icon(Icons.inventory_2_outlined),
                  selectedIcon: Icon(Icons.inventory_2),
                  label: 'Inventory',
                ),
              _Tab.overview => const NavigationDestination(
                  icon: Icon(Icons.insights_outlined),
                  selectedIcon: Icon(Icons.insights),
                  label: 'Overview',
                ),
              _Tab.history => const NavigationDestination(
                  icon: Icon(Icons.history_outlined),
                  selectedIcon: Icon(Icons.history),
                  label: 'History',
                ),
            },
        ],
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
      floatingActionButton: _currentTab == _Tab.inventory
          ? FilledButton.icon(
              onPressed: () => _openItemSheet(),
              icon: const Icon(Icons.add),
              label: const Text('Add item'),
            )
          : null,
    );
  }
}

class _InventoryList extends StatelessWidget {
  const _InventoryList({
    required this.items,
    required this.user,
    required this.onAdjust,
    required this.onOpen,
  });

  final List<InventoryItem> items;
  final AppUser user;
  final void Function(InventoryItem, double) onAdjust;
  final ValueChanged<InventoryItem> onOpen;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    final TextTheme text = Theme.of(context).textTheme;
    final int lowCount = items.where((InventoryItem i) => i.isLow).length;

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 96),
      children: <Widget>[
        Text(
          'Signed in as ${user.email} · ${user.role.label}',
          style: text.bodyMedium!.copyWith(color: scheme.onSurfaceVariant),
        ),
        if (lowCount > 0)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              '$lowCount item${lowCount == 1 ? '' : 's'} running low',
              style: text.titleMedium!.copyWith(color: scheme.error),
            ),
          ),
        for (final String category in kInventoryCategories)
          if (items.any((InventoryItem i) => i.category == category)) ...<Widget>[
            Padding(
              padding: const EdgeInsets.only(top: 24, bottom: 8),
              child: Text(category, style: text.titleLarge),
            ),
            for (final InventoryItem item in items
                .where((InventoryItem i) => i.category == category))
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _ItemCard(
                  item: item,
                  onAdjust: onAdjust,
                  onOpen: onOpen,
                ),
              ),
          ],
      ],
    );
  }
}

class _ItemCard extends StatelessWidget {
  const _ItemCard({
    required this.item,
    required this.onAdjust,
    required this.onOpen,
  });

  final InventoryItem item;
  final void Function(InventoryItem, double) onAdjust;
  final ValueChanged<InventoryItem> onOpen;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    final TextTheme text = Theme.of(context).textTheme;

    return Card(
      key: Key('item-${item.id}'),
      child: InkWell(
        onTap: () => onOpen(item),
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Row(
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Flexible(
                          child: Text(
                            item.name,
                            style: text.bodyLarge,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (item.isLow) ...<Widget>[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 3,
                            ),
                            decoration: BoxDecoration(
                              color: scheme.errorContainer,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              'Low',
                              style: text.labelLarge!.copyWith(
                                color: scheme.onErrorContainer,
                                fontSize: 13,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${item.unit} · should have ${formatQuantity(item.par)}',
                      style: text.bodyMedium!.copyWith(
                        color: scheme.onSurfaceVariant,
                      ),
                    ),
                    if (item.lastCountedBy != null) ...<Widget>[
                      const SizedBox(height: 2),
                      Text(
                        'Counted by ${shortEmailName(item.lastCountedBy!)} '
                        '· ${formatWhen(item.lastCountedAt!)}',
                        style: text.bodyMedium!.copyWith(
                          color: scheme.onSurfaceVariant,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ],
                ),
              ),
              IconButton.filledTonal(
                key: Key('dec-${item.id}'),
                tooltip: 'Remove one',
                icon: const Icon(Icons.remove),
                onPressed:
                    item.quantity <= 0 ? null : () => onAdjust(item, -1),
              ),
              SizedBox(
                width: 48,
                child: Text(
                  formatQuantity(item.quantity),
                  textAlign: TextAlign.center,
                  style: text.titleMedium,
                ),
              ),
              IconButton.filledTonal(
                key: Key('inc-${item.id}'),
                tooltip: 'Add one',
                icon: const Icon(Icons.add),
                onPressed: () => onAdjust(item, 1),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _OverviewTab extends StatelessWidget {
  const _OverviewTab({required this.items});

  final List<InventoryItem> items;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    final TextTheme text = Theme.of(context).textTheme;
    final List<InventoryItem> lowItems =
        items.where((InventoryItem i) => i.isLow).toList();

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 96),
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: _StatCard(label: 'Items tracked', value: '${items.length}'),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _StatCard(
                label: 'Running low',
                value: '${lowItems.length}',
                highlight: lowItems.isNotEmpty,
              ),
            ),
          ],
        ),
        const SizedBox(height: 28),
        Text('Shopping list', style: text.titleLarge),
        const SizedBox(height: 12),
        if (lowItems.isEmpty)
          Text(
            'Everything is fully stocked. Nothing to order.',
            style: text.bodyLarge,
          )
        else
          for (final InventoryItem item in lowItems)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(item.name, style: text.bodyLarge),
                      const SizedBox(height: 4),
                      Text(
                        'Have ${formatQuantity(item.quantity)} ${item.unit} · '
                        'need ${formatQuantity(item.par - item.quantity)} more',
                        style: text.bodyMedium!.copyWith(
                          color: scheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
      ],
    );
  }
}

/// Every change, newest first: counts, added/edited/removed items.
class _HistoryTab extends StatelessWidget {
  const _HistoryTab({required this.entries});

  final List<HistoryEntry> entries;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    final TextTheme text = Theme.of(context).textTheme;

    if (entries.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text(
            'No changes yet.\nCounts and edits will show up here.',
            textAlign: TextAlign.center,
            style: text.bodyLarge!.copyWith(color: scheme.onSurfaceVariant),
          ),
        ),
      );
    }
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
      children: <Widget>[
        for (final HistoryEntry entry in entries)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(entry.message, style: text.bodyLarge),
                    const SizedBox(height: 4),
                    Text(
                      '${shortEmailName(entry.by)} · ${formatWhen(entry.at)}',
                      style: text.bodyMedium!.copyWith(
                        color: scheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.label,
    required this.value,
    this.highlight = false,
  });

  final String label;
  final String value;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    final TextTheme text = Theme.of(context).textTheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              label,
              style: text.bodyMedium!.copyWith(color: scheme.onSurfaceVariant),
            ),
            const SizedBox(height: 4),
            Text(
              value,
              style: text.headlineMedium!.copyWith(
                color: highlight ? scheme.error : scheme.onSurface,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ItemSheetResult {
  const _ItemSheetResult.save(this.item) : delete = false;

  const _ItemSheetResult.delete()
      : item = null,
        delete = true;

  final InventoryItem? item;
  final bool delete;
}

/// Bottom sheet for adding or editing an item.
class _ItemSheet extends StatefulWidget {
  const _ItemSheet({required this.item});

  final InventoryItem? item;

  @override
  State<_ItemSheet> createState() => _ItemSheetState();
}

class _ItemSheetState extends State<_ItemSheet> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  late final TextEditingController _name =
      TextEditingController(text: widget.item?.name ?? '');
  late final TextEditingController _unit =
      TextEditingController(text: widget.item?.unit ?? '');
  late final TextEditingController _quantity = TextEditingController(
    text: widget.item == null ? '' : formatQuantity(widget.item!.quantity),
  );
  late final TextEditingController _par = TextEditingController(
    text: widget.item == null ? '' : formatQuantity(widget.item!.par),
  );
  late String _category = widget.item?.category ?? 'Produce';

  @override
  void dispose() {
    _name.dispose();
    _unit.dispose();
    _quantity.dispose();
    _par.dispose();
    super.dispose();
  }

  void _save() {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    final InventoryItem? original = widget.item;
    final double quantity =
        double.tryParse(_quantity.text.trim()) ?? original?.quantity ?? 0;
    final double par =
        double.tryParse(_par.text.trim()) ?? original?.par ?? 0;
    final String unit = _unit.text.trim();
    final InventoryItem item = InventoryItem(
      id: original?.id ??
          DateTime.now().millisecondsSinceEpoch.toString(),
      name: _name.text.trim(),
      category: _category,
      unit: unit.isEmpty ? 'each' : unit,
      quantity: max(0, quantity),
      par: max(0, par),
      lastCountedBy: original?.lastCountedBy,
      lastCountedAt: original?.lastCountedAt,
    );
    Navigator.of(context).pop(_ItemSheetResult.save(item));
  }

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    final TextTheme text = Theme.of(context).textTheme;
    final String title = widget.item == null ? 'Add item' : 'Edit item';

    return Padding(
      padding: EdgeInsets.fromLTRB(
        24,
        24,
        24,
        24 + MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Text(title, style: text.titleLarge),
            const SizedBox(height: 16),
            TextFormField(
              key: const Key('name-field'),
              controller: _name,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                labelText: 'Name',
                border: OutlineInputBorder(),
              ),
              validator: (String? value) =>
                  (value ?? '').trim().isEmpty ? 'Give the item a name.' : null,
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              key: const Key('category-field'),
              initialValue: _category,
              decoration: const InputDecoration(
                labelText: 'Category',
                border: OutlineInputBorder(),
              ),
              items: <DropdownMenuItem<String>>[
                for (final String category in kInventoryCategories)
                  DropdownMenuItem<String>(
                    value: category,
                    child: Text(category),
                  ),
              ],
              onChanged: (String? value) =>
                  setState(() => _category = value ?? _category),
            ),
            const SizedBox(height: 12),
            Row(
              children: <Widget>[
                Expanded(
                  child: TextFormField(
                    key: const Key('unit-field'),
                    controller: _unit,
                    decoration: const InputDecoration(
                      labelText: 'Unit',
                      hintText: 'lbs',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    key: const Key('qty-field'),
                    controller: _quantity,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Count',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    key: const Key('par-field'),
                    controller: _par,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Should have',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            FilledButton(
              key: const Key('sheet-save'),
              onPressed: _save,
              child: const Text('Save'),
            ),
            if (widget.item != null) ...<Widget>[
              const SizedBox(height: 8),
              TextButton(
                style: TextButton.styleFrom(foregroundColor: scheme.error),
                onPressed: () => Navigator.of(context)
                    .pop(const _ItemSheetResult.delete()),
                child: const Text('Delete item'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
