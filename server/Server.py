from flask import render_template
from flask import Flask, request, send_file
from werkzeug.utils import secure_filename
import os
import logging
import glob
from flask import jsonify
import shutil
from filelock import FileLock

TRIMMED_LOGS = False

# Output in a preferred format.
if TRIMMED_LOGS:
    logging.basicConfig(level=logging.INFO, format='%(message)s')
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

# Initialize the flask
app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

SEPARATOR = "/"
WORKDIR = "userfiles/"

@app.route('/')
def hello_world():
    return render_template('home.html')

# Propagating Flask logs back to gunicorn.

# stream_handler = logging.StreamHandler()
# stream_handler.setLevel(logging.info)
# app.logger.addHandler(stream_handler)

# stream_handler = logging.StreamHandler()
# stream_handler.setLevel(logging.WARNING)
# app.logger.addHandler(stream_handler)

# https://github.com/benoitc/gunicorn/issues/1124


# Run from one of the clients as the initial step
@app.route('/init/<dirname>', methods=['POST']) # POST has u and ym
def init(dirname=None):
    logging.info("Init Request received for: %s", dirname)
    # Get the file from the POST request
    f1 = request.files['file1']
    f2 = request.files['file2']
    if os.path.exists(WORKDIR + secure_filename(dirname)):
        files = glob.glob(WORKDIR + secure_filename(dirname) + SEPARATOR + "*")
        for f in files:
            os.remove(f)
    else:
        os.makedirs(WORKDIR + secure_filename(dirname))
    f1.save(WORKDIR + secure_filename(dirname) + SEPARATOR + secure_filename(f1.filename))
    f2.save(WORKDIR + secure_filename(dirname) + SEPARATOR + secure_filename(f2.filename))

    resp = jsonify(success=True)
    return resp


# Run when a POST is made to /ctl/<dirname>?fetch=<returnfile>. For example, /ctl/test?fetch=u
@app.route('/ctl/<dirname>', methods=['POST'])
def ctl(dirname=None):
    logging.info("CTL Request received for: %s", dirname)
    return_file = request.args.get('fetch')
    f1 = request.files['file1']
    file_content = f1.read()
    f1.close()
    logging.info("[CTL] %s", file_content)

    with FileLock(WORKDIR + secure_filename(dirname) + SEPARATOR + secure_filename(f1.filename) + ".lock"):
        logging.info("[CTL] Lock acquired for %s : %s", dirname, f1.filename)
        with open(WORKDIR + secure_filename(dirname) + SEPARATOR + secure_filename(f1.filename), 'wb') as file_output:
            file_output.write(file_content)
            file_output.close()

    with FileLock(WORKDIR + secure_filename(dirname) + SEPARATOR + return_file + ".lock"):
        logging.info("[CTL] Lock acquired for %s : %s", dirname, return_file)
        return send_file(WORKDIR + secure_filename(dirname) + SEPARATOR + return_file, mimetype='text/plain')


# Run when a POST is made to /pm/<dirname>?fetch=<returnfile>. For example, /pm/test?fetch=ym
@app.route('/pm/<dirname>', methods=['POST'])
def pm(dirname=None):
    logging.info("PM request received for: %s", dirname)
    return_file = request.args.get('fetch')
    f1 = request.files['file1']
    file_content = f1.read()
    f1.close()
    logging.info("[PM] %s", file_content)

    with FileLock(WORKDIR + secure_filename(dirname) + SEPARATOR + secure_filename(f1.filename) + ".lock"):
        logging.info("[PM] Lock acquired for %s : %s", dirname, f1.filename)
        with open(WORKDIR + secure_filename(dirname) + SEPARATOR + secure_filename(f1.filename), 'wb') as file_output:
            file_output.write(file_content)
            file_output.close()

    with FileLock(WORKDIR + secure_filename(dirname) + SEPARATOR + return_file + ".lock"):
        logging.info("[PM] Lock acquired for %s : %s", dirname, return_file)
        return send_file(WORKDIR + secure_filename(dirname) + SEPARATOR + return_file, mimetype='text/plain')


# Run from one of the clients as the final step
@app.route('/cleanup/<dirname>', methods=['DELETE'])
def cleanup(dirname=None):
    logging.info("Cleanup Request received for: %s", dirname)
    if os.path.exists(WORKDIR + secure_filename(dirname)):
        shutil.rmtree(WORKDIR + secure_filename(dirname))

    resp = jsonify(success=True)
    return resp


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
