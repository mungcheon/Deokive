import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../l10n/generated/app_localizations.dart';
import '../state/app_state.dart';
import 'support_detail_screen.dart';

class SupportListScreen extends StatelessWidget {
  const SupportListScreen({super.key});

  String formatDate(DateTime date) {
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final inquiries = [...appState.inquiries.reversed];

        return Scaffold(
          appBar: AppBar(title: Text(l.myInquiries)),
          body: inquiries.isEmpty
              ? Center(
                  child: Text(
                    l.noInquiries,
                    style: const TextStyle(fontSize: 16),
                  ),
                )
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: inquiries.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final inquiry = inquiries[index];

                    return Card(
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(18),
                        side: BorderSide(color: Colors.grey.shade300),
                      ),
                      child: ListTile(
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 10,
                        ),
                        leading: CircleAvatar(
                          backgroundColor: inquiry.isAnswered
                              ? Colors.green.shade50
                              : Colors.orange.shade50,
                          child: Icon(
                            inquiry.isAnswered
                                ? Icons.mark_email_read_outlined
                                : Icons.mark_email_unread_outlined,
                            color: inquiry.isAnswered
                                ? Colors.green
                                : Colors.orange,
                          ),
                        ),
                        title: Text(
                          inquiry.title,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                        subtitle: Text(
                          '${inquiry.isAnswered ? l.inquiryAnswered : l.inquiryPending} · ${formatDate(inquiry.createdAt)}',
                        ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => SupportDetailScreen(
                                inquiryId: inquiry.id,
                              ),
                            ),
                          );
                        },
                      ),
                    );
                  },
                ),
        );
      },
    );
  }
}
