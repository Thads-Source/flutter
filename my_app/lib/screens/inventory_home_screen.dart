import 'dart:math';

import 'package:flutter/material.dart';

import '../auth/auth_service.dart';
import '../inventory/inventory_store.dart';
import '../models/inventory_item.dart';

/// The main screen after signing in.
///
/// Kitchen staff see the inventory list and update counts with big +/-
/// buttons. Managers and owners additionally get an Overview tab (stock
/// stats and a shopping list of everything below par) and can add, edit,
/// and delete items.
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
  int _tab = 0;

  bool get _canManage => widget.user.role.canManageItems;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final List<InventoryItem> items = await _store.load();
    if (!mounted) {
      return;
    }
    setState(() => _items = items);
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
      builder: (_) => _ItemSheet(item: item, canManage: _canManage),
    );
    if (result == null) {
      return;
    }
    await _apply(() {
      if (result.delete) {
        _items!.removeWhere((InventoryItem i) => i.id == item!.id);
      } else if (item == null) {
        _items!.add(result.item!);
      } else {
        final int index =
            _items!.indexWhere((InventoryItem i) => i.id == item.id);
        _items![index] = result.item!;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final List<InventoryItem>? items = _items;
    if (items == null) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(_tab == 0 ? 'Inventory' : 'Overview'),
        actions: <Widget>[
          IconButton(
            tooltip: 'Sign out',
            icon: const Icon(Icons.logout),
            onPressed: widget.onSignOut,
          ),
        ],
      ),
      body: _tab == 0
          ? _InventoryList(
              items: items,
              user: widget.user,
              onAdjust: (InventoryItem item, double delta) => _apply(
                () => item.quantity = max(0, item.quantity + delta),
              ),
              onOpen: (InventoryItem item) => _openItemSheet(item: item),
            )
          : _OverviewTab(items: items),
      bottomNavigationBar: _canManage
          ? NavigationBar(
              selectedIndex: _tab,
              onDestinationSelected: (int index) =>
                  setState(() => _tab = index),
              destinations: const <NavigationDestination>[
                NavigationDestination(
                  icon: Icon(Icons.inventory_2_outlined),
                  selectedIcon: Icon(Icons.inventory_2),
                  label: 'Inventory',
                ),
                NavigationDestination(
                  icon: Icon(Icons.insights_outlined),
                  selectedIcon: Icon(Icons.insights),
                  label: 'Overview',
                ),
              ],
            )
          : null,
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
      floatingActionButton: _tab == 0 && _canManage
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
              '$lowCount item${lowCount == 1 ? '' : 's'} below par',
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
                      '${item.unit} · par ${formatQuantity(item.par)}',
                      style: text.bodyMedium!.copyWith(
                        color: scheme.onSurfaceVariant,
                      ),
                    ),
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
                label: 'Below par',
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
            'Everything is at or above par. Nothing to order.',
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
                        'need ${formatQuantity(item.par - item.quantity)} more '
                        'to reach par',
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

/// Bottom sheet for adding/editing an item (managers and owners) or just
/// updating its count (kitchen staff).
class _ItemSheet extends StatefulWidget {
  const _ItemSheet({required this.item, required this.canManage});

  final InventoryItem? item;
  final bool canManage;

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
      name: widget.canManage ? _name.text.trim() : original!.name,
      category: widget.canManage ? _category : original!.category,
      unit: widget.canManage
          ? (unit.isEmpty ? 'each' : unit)
          : original!.unit,
      quantity: max(0, quantity),
      par: widget.canManage ? max(0, par) : original!.par,
    );
    Navigator.of(context).pop(_ItemSheetResult.save(item));
  }

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    final TextTheme text = Theme.of(context).textTheme;
    final String title;
    if (widget.item == null) {
      title = 'Add item';
    } else if (widget.canManage) {
      title = 'Edit item';
    } else {
      title = 'Update count';
    }

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
            if (widget.canManage) ...<Widget>[
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
            ],
            Row(
              children: <Widget>[
                if (widget.canManage) ...<Widget>[
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
                ],
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
                if (widget.canManage) ...<Widget>[
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      key: const Key('par-field'),
                      controller: _par,
                      keyboardType: const TextInputType.numberWithOptions(
                        decimal: true,
                      ),
                      decoration: const InputDecoration(
                        labelText: 'Par',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 24),
            FilledButton(
              key: const Key('sheet-save'),
              onPressed: _save,
              child: const Text('Save'),
            ),
            if (widget.canManage && widget.item != null) ...<Widget>[
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
