from src.utils.constants import PACKAGE_CATALOG as C
n = sum(len(v) for v in C.values())
print("kategori:", len(C), "| toplam paket:", n)
print()
for k, v in C.items():
    print(f"  {k:28} {len(v)}")
print()
hepsi = {str(p).lower() for v in C.values() for p in v}
for a in ["gdal", "ffmpeg", "cuda-toolkit", "gcc", "nodejs", "postgresql", "r-base"]:
    print(f"  {a:14}", "VAR" if a in hepsi else "YOK")
