from __future__ import annotations

import sys


def main() -> int:
    from electro_sim.app import create_app
    app, window = create_app(sys.argv)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
