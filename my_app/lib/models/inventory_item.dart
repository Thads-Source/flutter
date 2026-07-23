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
  });

  factory InventoryItem.fromJson(Map<String, dynamic> json) => InventoryItem(
        id: json['id'] as String,
        name: json['name'] as String,
        category: json['category'] as String,
        unit: json['unit'] as String,
        quantity: (json['quantity'] as num).toDouble(),
        par: (json['par'] as num).toDouble(),
      );

  final String id;
  String name;
  String category;
  String unit;
  double quantity;
  double par;

  bool get isLow => quantity < par;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'id': id,
        'name': name,
        'category': category,
        'unit': unit,
        'quantity': quantity,
        'par': par,
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
