import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/history_entry.dart';
import '../models/inventory_item.dart';

/// Loads and saves the inventory list and change history from device
/// storage. First launch seeds a realistic starter inventory so the app is
/// usable immediately.
class InventoryStore {
  static const String _itemsKey = 'inventory_items';
  static const String _historyKey = 'inventory_history';

  /// The history is capped so storage never grows without bound.
  static const int maxHistoryEntries = 200;

  Future<List<InventoryItem>> load() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    final String? raw = prefs.getString(_itemsKey);
    if (raw == null) {
      final List<InventoryItem> seed = _seedItems();
      await save(seed);
      return seed;
    }
    return (jsonDecode(raw) as List<dynamic>)
        .map((dynamic e) => InventoryItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> save(List<InventoryItem> items) async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _itemsKey,
      jsonEncode(items.map((InventoryItem i) => i.toJson()).toList()),
    );
  }

  Future<List<HistoryEntry>> loadHistory() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    final String? raw = prefs.getString(_historyKey);
    if (raw == null) {
      return <HistoryEntry>[];
    }
    return (jsonDecode(raw) as List<dynamic>)
        .map((dynamic e) => HistoryEntry.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> saveHistory(List<HistoryEntry> entries) async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _historyKey,
      jsonEncode(
        entries
            .take(maxHistoryEntries)
            .map((HistoryEntry e) => e.toJson())
            .toList(),
      ),
    );
  }

  List<InventoryItem> _seedItems() => <InventoryItem>[
        InventoryItem(id: 'chicken-breast', name: 'Chicken breast', category: 'Proteins', unit: 'lbs', quantity: 12, par: 10),
        InventoryItem(id: 'ground-beef', name: 'Ground beef', category: 'Proteins', unit: 'lbs', quantity: 4, par: 8),
        InventoryItem(id: 'tomatoes', name: 'Tomatoes', category: 'Produce', unit: 'lbs', quantity: 6, par: 5),
        InventoryItem(id: 'onions', name: 'Onions', category: 'Produce', unit: 'lbs', quantity: 3, par: 6),
        InventoryItem(id: 'milk', name: 'Milk', category: 'Dairy', unit: 'gal', quantity: 4, par: 4),
        InventoryItem(id: 'butter', name: 'Butter', category: 'Dairy', unit: 'lbs', quantity: 2, par: 4),
        InventoryItem(id: 'rice', name: 'Rice', category: 'Dry Goods', unit: 'lbs', quantity: 25, par: 15),
        InventoryItem(id: 'flour', name: 'Flour', category: 'Dry Goods', unit: 'lbs', quantity: 20, par: 10),
        InventoryItem(id: 'gloves', name: 'Gloves', category: 'Supplies', unit: 'boxes', quantity: 5, par: 3),
      ];
}
