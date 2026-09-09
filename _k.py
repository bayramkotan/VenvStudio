import re
src = open("src/gui/launcher_ui.py", encoding="utf-8").read()
names = re.findall(r'"name":\s*"([^"]+)"', src)
print("tanimli kart sayisi:", len(names))
for a in ("Prefect", "Evidently", "Notebook (classic)"):
    print(" ", a, "VAR" if a in names else "YOK")
