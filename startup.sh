redis-server --daemonize yes  --dbfilename dump.rdb --dir /var/sessions
redis-cli CONFIG SET save "10 1"
python run.py
