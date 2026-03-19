"""
Bu scripti C:\Github\VenvStudio klasöründe çalıştır:
  python fix_terminal.py
"""
from pathlib import Path

file = Path("src/utils/platform_utils.py")
text = file.read_text(encoding="utf-8")

old = '''            elif terminal_type == "wt":
                cmd = f'start wt -d "{path}" cmd /k "{activate_bat}"'
'''

new = '''            elif terminal_type == "wt":
                if activate_ps1.exists():
                    cmd = (
                        f'start wt -d "{path}" powershell -NoExit -Command '
                        f'"& \\'{activate_ps1}\\'"'
                    )
                else:
                    cmd = f'start wt -d "{path}" cmd /k "{activate_bat}"'
'''

if old in text:
    text = text.replace(old, new)
    file.write_text(text, encoding="utf-8")
    print("✅ Düzeltildi!")
else:
    print("❌ Eşleşme bulunamadı — platform_utils.py değişmiş olabilir.")
    print("Manuel düzeltme:")
    print(new)
