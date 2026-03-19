"""
C:\Github\VenvStudio klasöründe çalıştır:
  python main_patch.py
"""
from pathlib import Path

file = Path("main.py")
text = file.read_text(encoding="utf-8")

old = '''        # Konsol açıksa kullanıcı okuyabilsin
        if getattr(sys, 'frozen', False):
            input("\\nPress Enter to exit...")'''

new = '''        # Konsol açıksa kullanıcı okuyabilsin (sadece debug/console build)
        if getattr(sys, 'frozen', False) and not getattr(sys, 'frozen_windowed', True):
            input("\\nPress Enter to exit...")'''

if old in text:
    text = text.replace(old, new)
    file.write_text(text, encoding="utf-8")
    print("✅ Düzeltildi!")
else:
    # Try alternate whitespace
    import re
    pattern = r'        # Konsol açıksa kullanıcı okuyabilsin\s+if getattr\(sys, .frozen., False\):\s+input\("\\nPress Enter to exit\.\.\."\)'
    if re.search(pattern, text):
        text = re.sub(pattern,
            '        # Konsol açıksa kullanıcı okuyabilsin (sadece debug/console build)\n'
            '        # --windowed modunda input() gizli konsol açar, kaldırıldı',
            text)
        file.write_text(text, encoding="utf-8")
        print("✅ Regex ile düzeltildi!")
    else:
        print("❌ Eşleşme bulunamadı. Manuel düzelt:")
        print("main.py içinde şu satırları sil:")
        print("  if getattr(sys, 'frozen', False):")
        print("      input('\\nPress Enter to exit...')")
