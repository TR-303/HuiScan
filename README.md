# 项目运行说明
运行
```bash
conda create -n HuiScan python=3.12
```
创建3.12版本的python环境，并使用
```bash
pip install -r requirements.txt
```
安装依赖
服务器启动前，在根目录运行
```bash
flask --app run.py init-db
```
创建数据库表
最后用
```bash
python run.py
```
启动开发服务器

若要清空数据库，可以使用
```bash
flask --app run.py reset-db
```
