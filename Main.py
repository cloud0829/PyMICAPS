# -*- coding: utf-8 -*-
#
#     Author:     Liu xianyao
#     Email:      flashlxy@qq.com
#     Update:     2017-04-11
#     Copyright:  ©江西省气象台 2017
#     Version:    2.0.20170411

import sys
import math
from itertools import takewhile
from FnTime import fn_timer


def parseInt(s):
    """
    全局函数 字符串转整数
    :param s: 字符串
    :return: 整数
    """
    assert isinstance(s, str)
    return (
        int("".join(list(takewhile(lambda x: x.isdigit(), s))))
        if s[0].isdigit()
        else None
    )


def equal(value1, value2):
    return math.fabs(value1 - value2) < 10e-5


@fn_timer
def run_draw(xml_path, debug=False):
    """
    运行绘图逻辑
    :param xml_path: 配置文件路径
    :param debug: 是否调试模式
    :return: 成功返回生成的图片路径，失败抛出异常
    """
    from Products import Products
    products = Products(xml_path)
    if products is not None:
        last_pic = None
        for micapsfile in products.micapsfiles:
            micapsfile.file.micapsdata.Draw(products, micapsfile, debug)
            last_pic = products.picture.picfile
        return last_pic
    else:
        raise Exception("无法加载配置文件或配置文件格式错误")

def start_server():
    from flask import Flask, request, jsonify, send_file
    from flask_cors import CORS
    import os
    import base64

    # 切换工作目录到 Main.py 所在目录，确保 XML 中的相对路径正确
    abs_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(abs_dir)

    app = Flask(__name__, static_url_path='', static_folder=abs_dir)
    CORS(app)

    CONFIG_PATH = os.path.join(abs_dir, "config.xml")

    @app.route('/api/config', methods=['GET'])
    def get_config():
        try:
            if not os.path.exists(CONFIG_PATH):
                return jsonify({"error": "Configuration file not found"}), 404
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return jsonify({"xml": f.read()})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/stations', methods=['GET'])
    def get_stations():
        try:
            stations_file = os.path.join(abs_dir, "SampleData", "stations.dat")
            if not os.path.exists(stations_file):
                return jsonify({"error": "Stations file not found"}), 404
            
            # 简单的 Diamond 17 解析器，避免循环引用
            stations = []
            import re
            for enc in ['utf-8', 'gbk']:
                try:
                    with open(stations_file, 'r', encoding=enc) as f:
                        content = f.read()
                    parts = re.split(r'\s+', content.strip())
                    if len(parts) < 4: continue
                    
                    station_sum = int(parts[3])
                    stations = []
                    for i in range(station_sum):
                        k = 4 + 7 * i
                        if k + 6 >= len(parts): break
                        stations.append({
                            "id": parts[k],
                            "lat": parts[k+1],
                            "lon": parts[k+2],
                            "height": parts[k+3],
                            "name": parts[k+6]
                        })
                    if stations: break
                except: continue

            if not stations:
                return jsonify({"error": "Failed to parse stations file"}), 400

            # 建立省份映射逻辑
            def get_province(code, name):
                c2 = code[:2]
                c3 = code[:3]
                if c3 == '545' or c3 == '544':
                    if '北京' in name or code in ['54398', '54399', '54406', '54416', '54419', '54421', '54424', '54431', '54433', '54499', '54511']:
                        return '北京市'
                    if '天津' in name or code in ['54517', '54527', '54428', '54523', '54525', '54623']:
                        return '天津市'
                
                mapping = {
                    '50': '黑龙江省', '51': '辽宁省', '52': '甘肃省', '53': '山西省', '54': '河北省',
                    '55': '西藏自治区', '56': '四川省', '57': '河南省', '58': '浙江省', '59': '广东省',
                    '61': '陕西省', '62': '甘肃省', '63': '青海省', '64': '宁夏回族自治区', '65': '新疆维吾尔自治区'
                }
                
                if c2 == '50':
                    if int(code) < 50500: return '黑龙江省'
                    return '内蒙古自治区'
                if c2 == '51':
                    if int(code) < 51400: return '辽宁省'
                    return '吉林省'
                if c2 == '52':
                    if int(code) < 52600: return '内蒙古自治区'
                    if int(code) < 52900: return '甘肃省'
                    return '宁夏回族自治区'
                if c2 == '53':
                    if int(code) < 53400: return '内蒙古自治区'
                    if int(code) < 53900: return '山西省'
                    return '河北省'
                if c2 == '54':
                    if int(code) < 54400: return '内蒙古自治区'
                    if int(code) >= 54700: return '山东省'
                    return '河北省'
                if c2 == '56':
                    if int(code) < 56300: return '四川省'
                    if int(code) < 56700: return '西藏自治区'
                    if int(code) < 56900: return '云南省'
                    return '贵州省'
                if c2 == '57':
                    if int(code) < 57400: return '河南省'
                    if int(code) < 57700: return '湖北省'
                    return '湖南省'
                if c2 == '58':
                    if code.startswith('5836'): return '上海市'
                    if int(code) < 58200: return '江苏省'
                    if int(code) < 58500: return '安徽省'
                    if int(code) < 58800: return '江西省'
                    return '浙江省'
                if c2 == '59':
                    if int(code) < 59200: return '福建省'
                    if int(code) < 59700: return '广东省'
                    if int(code) < 59900: return '海南省'
                    return '台湾省'
                return mapping.get(c2, '其他省份')

            # 聚合站点
            provinces = {}
            for s in stations:
                code = s['id']
                name = s['name']
                prov = get_province(code, name)
                if prov not in provinces:
                    provinces[prov] = []
                
                def parse_ll(val):
                    try:
                        if isinstance(val, float): return val
                        if '.' in val: return float(val)
                        v = float(val)
                        just = v // 100
                        return just + (v / 100 - just) * 100 / 60.0
                    except: return 0.0

                provinces[prov].append({
                    "id": code,
                    "name": name,
                    "lat": parse_ll(s['lat']),
                    "lon": parse_ll(s['lon']),
                    "height": float(s['height']) if s['height'] else 0.0
                })
            
            sorted_provinces = {k: provinces[k] for k in sorted(provinces.keys())}
            return jsonify(sorted_provinces)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/save_stations', methods=['POST'])
    def save_stations():
        try:
            data = request.json
            selected_stations = data.get('stations', [])
            if not selected_stations:
                return jsonify({"error": "No stations selected"}), 400
            
            # 创建临时站点文件
            temp_file = os.path.join(abs_dir, 'uploads', 'selected_stations.txt')
            os.makedirs(os.path.dirname(temp_file), exist_ok=True)
            
            with open(temp_file, 'w', encoding='gbk') as f:
                f.write("diamond 17 选定站点数据 {}\n".format(len(selected_stations)))
                for s in selected_stations:
                    # 格式：ID Lat(deg*100) Lon(deg*100) Height Class InfoSum Name
                    # 注意：Micaps 17 经纬度通常是 度分 格式，ChangeLL 会处理。
                    # 这里我们直接写度，Micaps17Data.ChangeLL 如果看到小数点会直接返回 float
                    f.write("{} {} {} {} 6 1 {}\n".format(
                        s['id'], s['lat'], s['lon'], s['height'], s['name']
                    ))
            
            return jsonify({
                "status": "success",
                "path": temp_file
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        try:
            if 'file' not in request.files:
                return jsonify({"error": "没有找到上传文件"}), 400
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "未选择文件"}), 400
            
            upload_dir = os.path.join(abs_dir, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, file.filename)
            file.save(file_path)
            
            # 解析基础信息 (获取文件大小和前两行内容)
            file_size = os.path.getsize(file_path)
            header_info = ""
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    lines = [f.readline().strip() for _ in range(2)]
                    header_info = " | ".join([line for line in lines if line])
            except:
                header_info = "非文本格式或编码不兼容"

            return jsonify({
                "status": "success",
                "path": file_path,
                "size": file_size,
                "header": header_info,
                "filename": file.filename
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/browse', methods=['GET'])
    def browse():
        try:
            import subprocess
            # 使用内联 python 脚本调用 tkinter，避免主线程冲突
            script = """
import sys, tkinter as tk, tkinter.filedialog as fd
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
path = fd.askopenfilename()
print(path)
"""
            result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
            path = result.stdout.strip()
            if path:
                # tkinter 返回的路径用正斜杠，转换成当前系统斜杠
                path = os.path.normpath(path)
            return jsonify({"path": path})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/render', methods=['POST'])
    def render():
        try:
            data = request.json
            xml_content = data.get('xml')
            if not xml_content:
                return jsonify({"error": "No XML content provided"}), 400

            # 覆盖原有配置文件
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            # 执行绘图
            pic_path = run_draw(CONFIG_PATH)

            if pic_path and os.path.exists(pic_path):
                # 如果是相对路径，转为绝对路径以便读取
                if not os.path.isabs(pic_path):
                    pic_path = os.path.join(abs_dir, pic_path)
                
                with open(pic_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                return jsonify({
                    "status": "success",
                    "image": encoded_string,
                    "path": pic_path
                })
            else:
                return jsonify({"error": "Drawing failed, no image generated"}), 500

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/')
    def index():
        return send_file(os.path.join(abs_dir, 'index.html'))

    print("Starting server at http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)

def main(debug):
    if debug:
        xml = r"config.xml"
    else:
        if len(sys.argv) < 2:
            print("参数不够，至少需要一个xml文件名参数")
            sys.exit()
        xml = sys.argv[1]
    run_draw(xml, debug)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        start_server()
    else:
        ISDEBUG = True
        main(ISDEBUG)
