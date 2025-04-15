启动服务器前，安装依赖，并在根目录运行
```bash
set FLASK_APP=run.py
flask init-db
```
创建数据库表

若要清空数据库，可以使用
```bash
set FLASK_APP=run.py
flask reset-db
```

目前可能导致报错：

$env:FLASK_APP = "run.py"

ModuleNotFoundError: No module named 'flask_sqlalchemy'

instance folder create

