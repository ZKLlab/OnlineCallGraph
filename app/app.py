# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import shutil
import hashlib
import traceback
import subprocess
from StringIO import StringIO
from PIL import Image
from flask import Flask, abort, render_template, request, send_file

app = Flask(__name__)

reload(sys)
sys.setdefaultencoding('utf-8')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/call_graph', methods=['POST'])
def call_graph():
    work_dir = os.getcwd()
    # Init Dir
    md5 = hashlib.md5()
    md5.update(os.urandom(32))
    base_dir = os.path.join(work_dir, 'call_graph', md5.hexdigest())
    os.mkdir(base_dir)
    main_cpp_path = os.path.join(base_dir, 'main.cpp')
    main_txt_path = os.path.join(base_dir, 'main.txt')
    main_dot_path = os.path.join(base_dir, 'main.dot')
    main_png_path = os.path.join(base_dir, 'main.png')
    # Limit the Max Size (16MB)
    if len(request.form['code']) > 1024 * 1024 * 16:
        abort(400)
    output_io = StringIO()
    # noinspection PyBroadException
    try:
        # Source Code to Tree
        with open(main_cpp_path, 'w') as fp:
            fp.write(request.form['code'])
        cflow_child = subprocess.Popen(
            ['cflow', '-d', '15', '-v', '-T', '-o', main_txt_path, main_cpp_path],
            stderr=subprocess.PIPE
        )
        for i in range(20):
            if cflow_child.poll() is not None:
                break
            time.sleep(0.1)
        else:
            cflow_child.kill()
            raise Exception('cFlow timeout.')
        print cflow_child.stderr.read()
        with open(main_txt_path, 'r') as fp:
            lines = fp.readlines()
        # Tree to Dot
        dot_pairs = []
        layers = []
        current_depth = 0
        for line in lines:
            pos = line.find('-')
            if pos == -1:
                continue
            if main_cpp_path not in line:
                continue
            match_result = re.findall(r'-(.*?)\(\)', line)
            if len(match_result) == 0:
                continue
            depth = int((pos + 1) / 2)
            if depth == current_depth + 1:
                layers.append(match_result[0])
            elif depth == current_depth:
                if current_depth == 1 and depth == 1:
                    dot_pairs.append([layers[0], None])
                layers[depth - 1] = match_result[0]
            elif depth < current_depth:
                layers[depth - 1] = match_result[0]
                del layers[depth:]
            else:
                continue
            current_depth = depth
            if len(layers) >= 2:
                dot_pairs.append([layers[-2], layers[-1]])
        if current_depth == 1:
            dot_pairs.append([layers[0], None])
        dot_pairs_set = []
        for item in dot_pairs:
            if item not in dot_pairs_set:
                dot_pairs_set.append(item)
        with open(main_dot_path, 'w') as fp:
            fp.write('digraph G{\n\trankdir=LR;\n\tnode [fontsize=24,shape=box];\n')
            for i1, i2 in dot_pairs_set:
                if i2 is None:
                    fp.write('\t"%s";\n' % i1)
                else:
                    fp.write('\t"%s" -> "%s";\n' % (i1, i2))
            fp.write('}')
        # Dot to Png
        dot_child = subprocess.Popen(['dot', '-Tpng', main_dot_path, '-o', main_png_path])
        for i in range(15):
            if dot_child.poll() is not None:
                break
            time.sleep(0.1)
        else:
            dot_child.kill()
            raise Exception('dot timeout.')
        # Convert to Standard Png
        Image.open(main_png_path).convert('L').convert('RGB').save(output_io, 'PNG')
    finally:
        traceback.print_exc()
        # Remove the Dir
        shutil.rmtree(base_dir, ignore_errors=True)
    output_io.seek(0)
    return send_file(output_io, mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
