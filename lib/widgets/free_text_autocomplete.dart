import 'package:flutter/material.dart';

import '../l10n/generated/app_localizations.dart';

/// Free-form text field that suggests previously-entered values while still
/// allowing the user to commit any string (typos included — those become new
/// distinct values by design).
///
/// `suggestions` is the deduped list of values already present in the data
/// store (e.g. `AppState.knownSeriesNames`). Filtering is case-insensitive
/// substring match.
class FreeTextAutocomplete extends StatelessWidget {
  final TextEditingController controller;
  final List<String> suggestions;
  final String labelText;
  final String? helperText;
  final bool required;
  final void Function(String value)? onChanged;

  const FreeTextAutocomplete({
    super.key,
    required this.controller,
    required this.suggestions,
    required this.labelText,
    this.helperText,
    this.required = false,
    this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Autocomplete<String>(
      initialValue: TextEditingValue(text: controller.text),
      optionsBuilder: (textEditingValue) {
        final input = textEditingValue.text.trim().toLowerCase();
        if (input.isEmpty) return suggestions.take(8);
        return suggestions
            .where((s) => s.toLowerCase().contains(input))
            .take(8);
      },
      onSelected: (value) {
        controller.text = value;
        onChanged?.call(value);
      },
      fieldViewBuilder:
          (context, fieldController, fieldFocusNode, onFieldSubmitted) {
        // Mirror the inner field's text to the outer controller so the form
        // can read the final committed value.
        fieldController.text = controller.text;
        fieldController.addListener(() {
          if (controller.text != fieldController.text) {
            controller.text = fieldController.text;
            onChanged?.call(fieldController.text);
          }
        });
        return TextField(
          controller: fieldController,
          focusNode: fieldFocusNode,
          onSubmitted: (_) => onFieldSubmitted(),
          decoration: InputDecoration(
            labelText: required ? '$labelText *' : labelText,
            helperText: helperText ?? l.autocompleteHint,
          ),
        );
      },
      optionsViewBuilder: (context, onSelected, options) {
        return Align(
          alignment: Alignment.topLeft,
          child: Material(
            elevation: 4,
            borderRadius: BorderRadius.circular(12),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 240, maxWidth: 360),
              child: ListView.builder(
                padding: EdgeInsets.zero,
                shrinkWrap: true,
                itemCount: options.length,
                itemBuilder: (context, index) {
                  final option = options.elementAt(index);
                  return ListTile(
                    dense: true,
                    title: Text(option),
                    onTap: () => onSelected(option),
                  );
                },
              ),
            ),
          ),
        );
      },
    );
  }
}
