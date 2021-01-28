if [ ! -f python-env/bin/activate ]; then
    python3 -m venv python-env
    source python-env/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
	source python-env/bin/activate
fi

python3 bot.py
