from app.views import *

# os.urandom(24)
app.secret_key = b'AA\x84o_\xc5I\xdc\xaf\x05\xcbZ\x9c\xb9\xa9\xacV5|c\xa7\x8dz\x9c'

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        debug=False,
        port=80
    )
