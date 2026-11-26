"""docrepro: reproduces photographed and scanned documents as digital documents.

One tool for one step (:mod:`docrepro.steps`): optdoc makes the page faithful, ocrdoc
recognises what is on it, semdoc and tagdoc are to understand and describe it.  docrepro
joins them: the chain and its document (:mod:`docrepro.chain`), one command line
(:mod:`docrepro.cli`), one window (:mod:`docrepro.gui`).  Every step, and so the whole way,
can be reproduced from the original and its configuration documents, byte for byte, and
resumed where a person stopped.  Everything runs locally.

What the tools share (configuration documents, the command line's manners, no network,
the window's building blocks) is doccor's (:mod:`doccor`).
"""

__version__ = "0.4.0"
