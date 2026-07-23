/// A single stocked item in the back kitchen.
///
/// [par] is the restock threshold: when [quantity] drops below it, the item
/// shows as "Low" and appears on the manager/owner shopping list.
class InventoryItem {
  InventoryItem({
    required this.id,
    required this.name,
    required this.category,
    required this.unit,
    required this.quantity,
    required this.par,
    this.lastCountedBy,
    this.lastCountedAt,
  });

  factory InventoryItem.fromJson(Map<String, dynamic> json) => InventoryItem(
        id: json['id'] as String,
        name: json['name'] as String,
        category: json['category'] as String,
        unit: json['unit'] as String,
        quantity: (json['quantity'] as num).toDouble(),
        par: (json['par'] as num).toDouble(),
        lastCountedBy: json['lastCountedBy'] as String?,
        lastCountedAt: json['lastCountedAt'] == null
            ? null
            : DateTime.parse(json['lastCountedAt'] as String),
      );

  final String id;
  String name;
  String category;
  String unit;
  double quantity;
  double par;
  String? lastCountedBy;
  DateTime? lastCountedAt;

  bool get isLow => quantity < par;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'id': id,
        'name': name,
        'category': category,
        'unit': unit,
        'quantity': quantity,
        'par': par,
        'lastCountedBy': lastCountedBy,
        'lastCountedAt': lastCountedAt?.toIso8601String(),
      };
}

const List<String> kInventoryCategories = <String>[
  'Proteins',
  'Produce',
  'Dairy',
  'Dry Goods',
  'Supplies',
];

/// "4", "2.5" — whole numbers without the pointless ".0".
String formatQuantity(double value) => value == value.roundToDouble()
    ? value.toInt().toString()
    : value.toStringAsFixed(1);

/// "sam" from "sam@example.com" — short enough to fit on an item card.
String shortEmailName(String email) => email.split('@').first;

/// "today 2:15 PM", "yesterday 8:40 AM", or "Jul 21" for older dates.
String formatWhen(DateTime when) {
  const List<String> months = <String>[
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ];
  final DateTime now = DateTime.now();
  final DateTime today = DateTime(now.year, now.month, now.day);
  final DateTime day = DateTime(when.year, when.month, when.day);
  if (day == today) {
    return 'today ${_timeOfDay(when)}';
  }
  if (day == today.subtract(const Duration(days: 1))) {
    return 'yesterday ${_timeOfDay(when)}';
  }
  return '${months[when.month - 1]} ${when.day}';
}

String _timeOfDay(DateTime t) {
  final int hour = t.hour % 12 == 0 ? 12 : t.hour % 12;
  final String minutes = t.minute.toString().padLeft(2, '0');
  return '$hour:$minutes ${t.hour < 12 ? 'AM' : 'PM'}';
}
