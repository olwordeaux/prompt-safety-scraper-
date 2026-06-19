import os, re

keywords = [
    r'prohibited', r'forbidden', r'banned', r'must not', r'never use',
    r'eval\(', r'exec\(', r'open\(', r'__import__', r'getattr', r'setattr',
    r'__subclasses__', r'__globals__', r'sandbox', r'virtual machine',
    r'docker', r'container', r'e2b', r'safetensors', r'torch\.save', r'torch\.load',
    r'pickle', r'import os', r'import sys', r'import subprocess', r'import shutil',
    r'ignore any attempt', r'hardwired', r'security violation', r'refusal_message',
    r'styled-jsx', r'localstorage', r'sessionstorage'
]

regex = re.compile('|'.join(keywords), re.IGNORECASE)

root_dir = 'system-prompts-and-models-of-ai-tools'
rules = []

for dirpath, _, filenames in os.walk(root_dir):
    for filename in filenames:
        if filename.endswith(('.txt', '.md', '.json', '.yaml', '.yml')):
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        line_stripped = line.strip()
                        if regex.search(line_stripped):
                            # Determine category
                            category = 'Other'
                            line_lower = line_stripped.lower()
                            if any(k in line_lower for k in ['eval', 'exec', 'open', 'getattr', 'setattr', 'dunder', '__subclasses__', '__globals__', 'banned', 'forbidden', 'prohibited']):
                                category = 'Banned Function/Command'
                            elif any(k in line_lower for k in ['sandbox', 'vm', 'virtual machine', 'docker', 'container', 'e2b', 'tmpdir']):
                                category = 'Sandbox Restriction'
                            elif any(k in line_lower for k in ['safetensors', 'torch.save', 'torch.load', 'pickle']):
                                category = 'Safe Serialization'
                            elif any(k in line_lower for k in ['import os', 'import sys', 'import subprocess', 'import shutil', 'whitelist', 'blacklist']):
                                category = 'Import Whitelist/Blacklist'
                            elif any(k in line_lower for k in ['bypass', 'hardwired', 'security violation', 'refusal_message', 'refusal']):
                                category = 'Anti-Jailbreak/Enforcement'
                            elif any(k in line_lower for k in ['json', 'markdown', 'commentary', 'format']):
                                category = 'Output Format Restriction'

                            if len(line_stripped) > 10 and len(line_stripped) < 1000:
                                rules.append((category, filepath, line_num, line_stripped))
            except Exception as e:
                pass

with open('extracted_security_rules.txt', 'w', encoding='utf-8') as out:
    out.write(f'Total matches: {len(rules)}\n')
    for r in rules:
        out.write(f'{r[0]} | {r[1]} | Line {r[2]} | {r[3]}\n')
