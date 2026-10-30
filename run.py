from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()  # Debug is deliberately off; Flask CLI can enable it locally.
