from src import create_app
from src.cli import init_db

app = create_app()
app.cli.add_command(init_db)

if __name__ == '__main__':
    app.run(debug=True)