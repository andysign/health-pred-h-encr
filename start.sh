# CreateEnv
if [ ! -d .venv ]; then
  python3.10 -m venv .venv;
fi;
# Activate
source ./.venv/bin/activate;
# UpgradeAndInstall
N=$(find .venv/lib/python3.10/site-packages/ -maxdepth 1 -type d | wc -l);
if [ $N -lt 10 ]; then
  pip install pip --upgrade;
  pip install -U pip wheel setuptools --ignore-installed;
  pip install -r requirements.txt --ignore-installed;
fi;
# PrepareDataAndDeploymentFiles
N=$(find data/ -maxdepth 1 -type f | wc -l);
if [ $N -lt 1 ]; then
  python dev.py;
fi;
# Start
python -W ignore app.py;
