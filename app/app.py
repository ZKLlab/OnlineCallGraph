import os
import re
import time
import shutil
import hashlib
import traceback
from PIL import Image
from flask import Flask, abort, render_template, request

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # work_dir = os.path.join(os.getcwd(), 'app')
        work_dir = '/var/www/app'
        # Init Dir
        md5 = hashlib.md5()
        md5.update(os.urandom(32))
        base_dir = os.path.join(work_dir, 'src', md5.hexdigest())
        os.mkdir(base_dir)
        main_cpp_path = os.path.join(base_dir, 'main.cpp')
        main_txt_path = os.path.join(base_dir, 'main.txt')
        main_dot_path = os.path.join(base_dir, 'main.dot')
        main_png_path = os.path.join(base_dir, 'main.png')
        png_path = os.path.join(work_dir, 'static/output', md5.hexdigest() + '.png')
        # Limit the Max Size (16MB)
        if len(request.form['code']) > 1024 * 1024 * 16:
            abort(400)
        try:
            # Source Code to Tree
            with open(main_cpp_path, 'w') as fp:
                fp.write(request.form['code'])
            os.system('cflow -T -m main -o %s %s' % (main_txt_path, main_cpp_path))
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
                    layers[depth - 1] = match_result[0]
                elif depth < current_depth:
                    layers[depth - 1] = match_result[0]
                    del layers[depth:]
                else:
                    continue
                current_depth = depth
                if len(layers) >= 2:
                    dot_pairs.append([layers[-2], layers[-1]])
            dot_pairs_set = []
            for item in dot_pairs:
                if item not in dot_pairs_set:
                    dot_pairs_set.append(item)
            with open(main_dot_path, 'w') as fp:
                fp.write('digraph G{\n\trankdir=LR;\n\tsize="2480,3508";\n\tnode [fontsize=24,shape=box];\n')
                for i1, i2 in dot_pairs_set:
                    fp.write('\t"%s" -> "%s";\n' % (i1, i2))
                fp.write('}')
            # Dot to Png
            os.system('dot -Tpng %s -o %s' % (main_dot_path, main_png_path))
            # Convert to Standard Png
            Image.open(main_png_path).convert('L').convert('RGB').save(png_path)
            # Remove the Dir
            shutil.rmtree(base_dir)
            for file_name in os.listdir(os.path.join(work_dir, 'static/output')):
                if os.path.getmtime(os.path.join(work_dir, 'static/output', file_name)) < time.time() - 24 * 60 * 60:
                    os.remove(os.path.getmtime(os.path.join(work_dir, file_name)))
            return render_template('index.html', img_src='/static/output/%s.png' % md5.hexdigest())
        except Exception as err:
            traceback.print_exc()
            # Try to Remove the Dir
            if os.path.exists(base_dir):
                shutil.rmtree(base_dir)
            return render_template('index.html', error=err)
    else:
        return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
