/// One line in the change history: who did what, and when.
class HistoryEntry {
  HistoryEntry({required this.at, required this.by, required this.message});

  factory HistoryEntry.fromJson(Map<String, dynamic> json) => HistoryEntry(
        at: DateTime.parse(json['at'] as String),
        by: json['by'] as String,
        message: json['message'] as String,
      );

  final DateTime at;
  final String by;
  final String message;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'at': at.toIso8601String(),
        'by': by,
        'message': message,
      };
}
