ChemHub v9.2 chemistry-aware extraction patch

Install:
  cd C:\chemhub_unified_product
  powershell -ExecutionPolicy Bypass -File .\Apply-ChemHub-AgentPatch.ps1

This patch only replaces apps/api/app/extractor.py and apps/api/app/processor.py.
It backs up the old files, copies the new files into the running api container,
and restarts api. It does not change database schema and does not touch site/admin/agent UI.

Main improvements:
- keeps all arrow conditions separately for display above arrow;
- fixes H2 oxidation state OCR: H2^0/H20 in redox context -> H2, not H2O;
- removes oxidation-state hints from usual formulas but preserves bracket charges;
- rejects cathode/anode/electron half-reactions and ionic equations;
- removes explanatory comments such as (оксид), (карбиды), (без горения);
- keeps reaction names such as синтез Рашига, метод Байера, тефлон;
- joins broken product lines ending with +;
- preserves cluster/complex charges such as [S8^2+], [Te6^4+], [AsF6-];
- deduplicates equivalent A+B->C+D / B+A->C+D / C+D->A+B reactions.
