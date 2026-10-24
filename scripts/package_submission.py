"""Create a self-contained HTML demo and a portable submission/source archive."""
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def main():
    html=(ROOT/'web/index.html').read_text()
    css=(ROOT/'web/styles.css').read_text()
    app=(ROOT/'web/app.js').read_text()
    engine=(ROOT/'web/engine.js').read_text()
    assets={}
    for p in [ROOT/'web/assets/model.json',ROOT/'web/assets/profiles.json',*sorted((ROOT/'web/assets/profiles').glob('*.json'))]:
        assets[p.relative_to(ROOT/'web').as_posix()]=json.loads(p.read_text())
    boot='window.THERMO_ASSETS='+json.dumps(assets,separators=(',',':')).replace('</','<\\/')+';\n'
    boot+='window.THERMO_ENGINE='+json.dumps(engine).replace('</','<\\/')+';\n'
    html=html.replace('<link rel="stylesheet" href="styles.css">','<style>'+css+'</style>')
    html=html.replace('<script src="app.js"></script>','<script>'+boot+'</script><script>'+app.replace('</script','<\\/script')+'</script>')
    standalone=ROOT/'ThermoGuard_Standalone.html';standalone.write_text(html)
    selected=[ROOT/'README.md',ROOT/'AUTHORS.md',standalone,ROOT/'server.py',ROOT/'Start.command',ROOT/'Start.bat',ROOT/'requirements-training.txt',ROOT/'data/ATTRIBUTION.md']
    for directory in ['web','src','tests','results','data/manifests']:
        selected.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    selected.extend(ROOT/'docs'/name for name in ['MODEL_CARD.md','DEMO_SCRIPT.md','SUBMISSION_RESULTS.md','references.md','project_proposal.md','implementation_plan.md'])
    selected.extend(ROOT/'artifacts'/name for name in ['dashboard.png','sample_predictions.csv','sample_experiment.json'])
    selected.append(ROOT/'output/pdf/EV_Motor_Thermal_Monitoring_Proposal.pdf')
    selected.extend(ROOT/'scripts'/name for name in ['train_submission.py','package_submission.py'])
    out=ROOT/'dist/ThermoGuard_Submission.zip';out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(set(selected)):
            if not p.exists():raise FileNotFoundError(p)
            z.write(p,Path('ThermoGuard_Motor')/p.relative_to(ROOT))
    print(f'Standalone: {standalone.stat().st_size/1024/1024:.1f} MB')
    print(f'ZIP: {out.stat().st_size/1024/1024:.1f} MB ({len(set(selected))} files)')

if __name__=='__main__':main()
