"""Main entrypoint."""
from verifiedfirst import create_app


def main() -> None:
    """Run the verifiedfirst web server."""
    app = create_app()
    app.run(host="0.0.0.0")


if __name__ == "__main__":
    main()
