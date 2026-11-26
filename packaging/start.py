"""The entry point of the standalone program: docrepro's command line, which holds every
step's own as well (``docrepro optdoc …``, ``docrepro ocrdoc …``, ``docrepro tagdoc …``)."""

from docrepro.cli import main

raise SystemExit(main())
