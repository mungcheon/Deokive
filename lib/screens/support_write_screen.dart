import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

class SupportWriteScreen extends StatefulWidget {
  const SupportWriteScreen({super.key});

  @override
  State<SupportWriteScreen> createState() => _SupportWriteScreenState();
}

class _SupportWriteScreenState extends State<SupportWriteScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _contentController = TextEditingController();
  String _category = '일반 문의';

  static const _categories = <String>[
    '일반 문의',
    '버그 제보',
    '계정 문의',
    '결제 문의',
    '기능 제안',
  ];

  @override
  void dispose() {
    _titleController.dispose();
    _contentController.dispose();
    super.dispose();
  }

  Future<void> _sendInquiry() async {
    if (!_formKey.currentState!.validate()) return;

    final subject = '[Deokive 문의] $_category - ${_titleController.text.trim()}';
    final body = '''
안녕하세요. Deokive 문의입니다.

카테고리
$_category

제목
${_titleController.text.trim()}

문의 내용
${_contentController.text.trim()}

기기 정보
Windows

답변 받을 이메일
''';

    final uri = Uri(
      scheme: 'mailto',
      path: 'deokivecs@gmail.com',
      queryParameters: {
        'subject': subject,
        'body': body,
      },
    );

    final launched = await launchUrl(uri);
    if (!mounted) return;

    if (!launched) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('메일 앱을 열 수 없습니다. 메일 앱 설정을 확인해 주세요.'),
        ),
      );
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('메일 작성 화면을 열었습니다. 보내기를 누르면 문의가 접수됩니다.'),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('문의하기')),
      body: SafeArea(
        child: Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const Text(
                '문의 메일 작성',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              Text(
                '문의 내용을 작성하면 deokivecs@gmail.com으로 메일 작성 화면이 열립니다.',
                style: TextStyle(color: Colors.grey.shade700, height: 1.5),
              ),
              const SizedBox(height: 20),
              DropdownButtonFormField<String>(
                value: _category,
                decoration: const InputDecoration(
                  labelText: '문의 카테고리',
                ),
                items: _categories
                    .map(
                      (item) => DropdownMenuItem<String>(
                        value: item,
                        child: Text(item),
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
                decoration: const InputDecoration(labelText: '제목'),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return '제목을 입력해 주세요.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _contentController,
                minLines: 6,
                maxLines: 10,
                decoration: const InputDecoration(
                  labelText: '문의 내용',
                  alignLabelWithHint: true,
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return '문의 내용을 입력해 주세요.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 24),
              SizedBox(
                height: 50,
                child: FilledButton(
                  onPressed: _sendInquiry,
                  child: const Text('메일 작성 열기'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
