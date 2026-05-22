ChemHub v10.2 patch

- Replaces mojibake/broken UTF-8 extractor, processor, agent main.jsx, and site main.jsx.
- Adds safe fallback local_hybrid_filter.py.
- Adds AI-agent delete-from-list button.
- Fixes M/X expansion inside formulas (2MH, KX).
- Strips oxidation states/charges from saved equations while keeping formula indices.
- Preserves conditions above arrow.
- Keeps deduplication, pKa/pKb/PR/cathode/anode rejection, line-merge, negative reactions, names.

Install:
powershell -ExecutionPolicy Bypass -File .\Apply-ChemHub-v10.2.ps1
