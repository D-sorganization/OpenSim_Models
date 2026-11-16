# Change fragment: remove the retired vendored GAAI tree

- Deletes the checked-in `.gaai/` tree. GAAI is retired fleet-wide.
- Guard test `test_gaai_removed_2725.py` fails if the tree or a launcher returns.
- Refs #2725. Refs #2727.
