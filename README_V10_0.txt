ChemHub v10.0 safe patch:
- fixes AI agent editor overwriting manual edits during live polling;
- expands generalized reactions M/X/Hal/Me/E in all positions, including MH -> NaH/LiH/KH;
- extracts conditions between arrows into metadata;
- preserves previous filters: pKa/pKb/PR, ion equations, cathode/anode, bad reactions;
- does not change PostgreSQL schema and does not touch site UI.
Install:
powershell -ExecutionPolicy Bypass -File .\Apply-ChemHub-v10.0.ps1
