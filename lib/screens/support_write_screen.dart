import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../l10n/generated/app_localizations.dart';

class SupportWriteScreen extends StatefulWidget {
  const SupportWriteScreen({super.key});

  @override
  State<SupportWriteScreen> createState() => _SupportWriteScreenState();
}

/// Stable category keys (stored / sent to backend). Display labels come from
/// `AppLocalizations.inquiryCategoryXxx`.
enum InquiryCategory { general, bug, account, payment, feature }

class _SupportWriteScreenState extends State<SupportWriteScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _contentController = TextEditingController();
  InquiryCategory _category = InquiryCategory.general;

  String _categoryLabel(AppLocalizations l, InquiryCategory c) {
    switch (c) {
      case InquiryCategory.general:
        return l.inquiryCategoryGeneral;
      case InquiryCategory.bug:
        return l.inquiryCategoryBug;
      case InquiryCategory.account:
        return l.inquiryCategoryAccount;
      case InquiryCategory.payment:
        return l.inquiryCategoryPayment;
      case InquiryCategory.feature:
        return l.inquiryCategoryFeature;
    }
  }

  @override
  void dispose() {
    _titleController.dispose();
    _contentController.dispose();
    super.dispose();
  }

  Future<void> _sendInquiry() async {
    if (!_formKey.currentState!.validate()) return;
    final l = AppLocalizations.of(context);
    final categoryLabel = _categoryLabel(l, _category);
    final subject = '[Deokive] $categoryLabel - ${_titleController.text.trim()}';
    final body = '''
$categoryLabel

${_titleController.text.trim()}

${_contentController.text.trim()}
''';

    final uri = Uri(
      scheme: 'mailto',
      path: 'deokivecs@gmail.com',
      queryParameters: {'subject': subject, 'body': body},
    );

    final launched = await launchUrl(uri);
    if (!mounted) return;

    if (!launched) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.mailLaunchFailed)),
      );
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(l.mailComposeOpened)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.support)),
      body: SafeArea(
        child: Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                l.supportFormHeader,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                l.supportFormDescription,
                style: TextStyle(color: Colors.grey.shade700, height: 1.5),
              ),
              const SizedBox(height: 20),
              DropdownButtonFormField<InquiryCategory>(
                value: _category,
                decoration: InputDecoration(labelText: l.inquiryCategoryLabel),
                items: InquiryCategory.values
                    .map(
                      (c) => DropdownMenuItem<InquiryCategory>(
                        value: c,
                        child: Text(_categoryLabel(l, c)),
                      ),
                    )
                    .toList(),
                onChanged: (value) {
                  if (value == null) return;
                  setState(() => _category = value);
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _titleController,
                decoration: InputDecoration(labelText: l.inquiryTitleLabel),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return l.inquiryTitleRequired;
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _contentController,
                minLines: 6,
                maxLines: 10,
                decoration: InputDecoration(
                  labelText: l.inquiryContentLabel,
                  alignLabelWithHint: true,
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return l.inquiryContentRequired;
                  }
                  return null;
                },
              ),
              const SizedBox(height: 24),
              SizedBox(
                height: 50,
                child: FilledButton(
                  onPressed: _sendInquiry,
                  child: Text(l.openMailComposer),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
