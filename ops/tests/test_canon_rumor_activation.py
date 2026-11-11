"""Canon rumor activation contract without requiring a running Evennia server."""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "spike/fvillage/world/rumors.py"
CORPUS = ROOT / "files/rumor-seeds-v0.1.md"
EXPECTED = {2, 3, 4, 151, 201, 236}


def load_pure_parser():
    """Extract the original parser, not a duplicated approximation."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    names = {"_strip_markup", "_parse_seed_line", "load_canon_rumors"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in names]
    selected = next(node for node in tree.body
                    if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "PLAYABLE_RUMOR_IDS"
                            for t in node.targets))
    module = ast.fix_missing_locations(ast.Module(body=[selected, *nodes], type_ignores=[]))
    namespace = {"re": re, "RUMOR_FILE": CORPUS}
    regex_nodes = [node for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id in
                           {"_SEED_RE", "_VARIANT_RE"} for target in node.targets)]
    exec(compile(ast.fix_missing_locations(ast.Module(body=regex_nodes, type_ignores=[])),
                 str(SOURCE), "exec"), namespace)
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace


class CanonRumorActivationTests(unittest.TestCase):
    def test_vetted_seeds_are_loaded_once_with_canonical_provenance(self):
        ns = load_pure_parser()
        self.assertEqual(ns["PLAYABLE_RUMOR_IDS"], EXPECTED)
        rows = ns["load_canon_rumors"]()
        self.assertEqual({r["canonical_seed_id"] for r in rows}, EXPECTED)
        self.assertEqual(len(rows), len(EXPECTED))
        for row in rows:
            self.assertTrue(row["claim"].strip())
            self.assertNotEqual(row["source_actor"], "village talk")
            self.assertNotIn("*Heard from:*", row["claim"])
            self.assertIsInstance(row["variants"], list)
        all_rows = ns["load_canon_rumors"](playable_only=False)
        self.assertEqual(len(all_rows), 250)
        self.assertEqual(len({r["canonical_seed_id"] for r in all_rows}), 250)

    def test_seed_activation_uses_existing_registry_and_preserves_existing_roots(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == "seed_playable_rumors")
        class Registry:
            def __init__(self):
                self.roots = {}
                self.hearings = set()
            def ensure_rumor(self, **fields):
                ident = fields["canonical_seed_id"]
                self.roots.setdefault(ident, dict(fields, id=ident))
                return self.roots[ident]
            def hear_direct(self, rumor_id, npc, **fields):
                self.hearings.add((rumor_id, npc.key))
        class NPC:
            key = "Rumor witness"
            location = None
        registry = Registry()
        ns = load_pure_parser()
        ns.update(get_rumor_registry=lambda: registry)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
                     str(SOURCE), "exec"), ns)
        first = ns["seed_playable_rumors"](participants=[NPC()])
        second = ns["seed_playable_rumors"](participants=[NPC()])
        self.assertEqual(len(first), 6)
        self.assertEqual(first, second)
        self.assertEqual(set(registry.roots), EXPECTED)
        self.assertEqual(len(registry.hearings), 6)
        for root in registry.roots.values():
            self.assertEqual(root["source_type"], "canon_teller")
            self.assertIsNone(root["original_event_id"])
            self.assertEqual(root["privacy"], "public")
            self.assertEqual(root["family"], f"canon:{root['canonical_seed_id']}")


if __name__ == "__main__":
    unittest.main()
